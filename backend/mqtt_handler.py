import json
import paho.mqtt.client as mqtt
from state_manager import get_websocket_clients, update_sensor, broadcast_state
from crud import save_blood_pressure, save_temperature, get_setting
from db import get_db
import asyncio
import logging

logger = logging.getLogger('mqtt_handler')

# Track latest sensor values
sensor_state = {}

def get_mqtt_settings():
    """Get MQTT settings from database"""
    db = next(get_db())
    try:
        settings = {}
        
        # Get basic MQTT settings
        settings['enabled'] = get_setting(db, 'mqtt_enabled', False)
        settings['broker'] = get_setting(db, 'mqtt_broker', '')
        settings['port'] = get_setting(db, 'mqtt_port', 1883)
        settings['username'] = get_setting(db, 'mqtt_username', '')
        settings['password'] = get_setting(db, 'mqtt_password', '')
        settings['client_id'] = get_setting(db, 'mqtt_client_id', 'sensor_monitor')
        
        # Get topic configurations
        topics_json = get_setting(db, 'mqtt_topics')
        if topics_json:
            try:
                # Handle both dict and JSON string cases
                if isinstance(topics_json, dict):
                    settings['topics'] = topics_json
                else:
                    settings['topics'] = json.loads(topics_json)
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"Failed to parse MQTT topics from database: {e}")
                settings['topics'] = {}
        else:
            settings['topics'] = {}
            
        return settings
    except Exception as e:
        logger.error(f"Error getting MQTT settings: {e}")
        return {
            'enabled': False,
            'broker': '',
            'port': 1883,
            'username': '',
            'password': '',
            'client_id': 'sensor_monitor',
            'topics': {}
        }
    finally:
        db.close()

def get_enabled_topics(mqtt_settings):
    """Get list of enabled topics from MQTT settings"""
    enabled_topics = {}
    
    for vital_name, config in mqtt_settings.get('topics', {}).items():
        if config.get('enabled', False):
            # Handle nutrition special case with 4 topics
            if vital_name == 'nutrition':
                enabled_topics['water_broadcast'] = config.get('water_broadcast_topic')
                enabled_topics['water_listen'] = config.get('water_listen_topic')
                enabled_topics['calories_broadcast'] = config.get('calories_broadcast_topic')
                enabled_topics['calories_listen'] = config.get('calories_listen_topic')
            else:
                # Standard vitals with broadcast and listen topics
                if config.get('broadcast_topic'):
                    enabled_topics[f'{vital_name}_broadcast'] = config['broadcast_topic']
                if config.get('listen_topic'):
                    enabled_topics[f'{vital_name}_listen'] = config['listen_topic']
    
    return enabled_topics

def get_mqtt_client(loop):
    """Create and configure MQTT client with database settings"""
    mqtt_settings = get_mqtt_settings()
    
    # Don't create client if MQTT is disabled
    if not mqtt_settings['enabled'] or not mqtt_settings['broker']:
        logger.info("MQTT disabled or no broker configured")
        return None
        
    client = mqtt.Client(client_id=mqtt_settings['client_id'])

    if mqtt_settings['username'] and mqtt_settings['password']:
        client.username_pw_set(mqtt_settings['username'], mqtt_settings['password'])

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            logger.info(f"Connected to MQTT Broker at {mqtt_settings['broker']}:{mqtt_settings['port']}")
            
            # Subscribe to all enabled topics
            enabled_topics = get_enabled_topics(mqtt_settings)
            for topic_name, topic_path in enabled_topics.items():
                # SUBSCRIBE TO LISTEN TOPICS, NOT BROADCAST/STATE
                if topic_path and 'listen' in topic_name:
                    client.subscribe(topic_path)
                    logger.info(f"Subscribed to {topic_path}")
        else:
            logger.error(f"Failed to connect to MQTT Broker, code {rc}")

    def on_message(client, userdata, msg):
        raw_data = msg.payload.decode()
        logger.info(f"MQTT Message received on {msg.topic}: {raw_data}")
        
        # Find which vital this topic belongs to
        matching_vital = None
        for vital_name, config in mqtt_settings.get('topics', {}).items():
            if not config.get('enabled', False):
                continue
                
            if vital_name == 'nutrition':
                if (msg.topic == config.get('water_listen_topic') or 
                    msg.topic == config.get('calories_listen_topic')):
                    matching_vital = vital_name
                    break
            else:
                if msg.topic == config.get('listen_topic'):
                    matching_vital = vital_name
                    break

        if matching_vital:
            try:
                payload = json.loads(raw_data)
                
                # Ignore messages that originated from this client to prevent loops
                if payload.get('origin') == mqtt_settings['client_id']:
                    logger.info(f"Ignoring message from our own client: {msg.topic}")
                    return
                
                # Handle blood pressure data (updated from "map" to "bp")
                if matching_vital == "blood_pressure":
                    systolic = payload.get("systolic")
                    diastolic = payload.get("diastolic")
                    map_value = payload.get("map")
                    
                    # Save to database if we have all valid values
                    if (systolic is not None and diastolic is not None and map_value is not None and
                        not (systolic == 0 and diastolic == 0 and map_value == 0)):
                        db = next(get_db())
                        try:
                            save_blood_pressure(
                                db=db,
                                systolic=systolic,
                                diastolic=diastolic,
                                map_value=map_value,
                                raw_data=raw_data
                            )
                            # Use update_sensor instead of broadcast_state to maintain consistency
                            update_sensor(("systolic_bp", systolic), ("diastolic_bp", diastolic), ("map_bp", map_value), from_mqtt=True)
                        finally:
                            db.close()
                    else:
                        logger.info(f"Ignoring invalid BP values: systolic={systolic}, diastolic={diastolic}, map={map_value}")
                
                # Handle temperature data
                elif matching_vital == "temperature":
                    skin_temp = payload.get("skin_temp")
                    body_temp = payload.get("body_temp")
                    
                    if (skin_temp is not None and body_temp is not None and
                        not (skin_temp == 0 and body_temp == 0)):
                        db = next(get_db())
                        try:
                            save_temperature(
                                db=db,
                                skin_temp=skin_temp,
                                body_temp=body_temp,
                                raw_data=raw_data
                            )
                            update_sensor(("skin_temp", skin_temp), from_mqtt=True)
                            update_sensor(("body_temp", body_temp), from_mqtt=True)
                            # Removed extra broadcast_state() call since update_sensor already handles it
                        finally:
                            db.close()
                    else:
                        logger.info(f"Ignoring invalid temperature values: skin_temp={skin_temp}, body_temp={body_temp}")
                
                # Handle nutrition data (water and calories)
                elif matching_vital == "nutrition":
                    water_config = mqtt_settings['topics']['nutrition']
                    if msg.topic == water_config.get('water_listen_topic'):
                        water_value = payload.get("water")
                        if water_value is not None:
                            update_sensor(("water", water_value), from_mqtt=True)
                    elif msg.topic == water_config.get('calories_listen_topic'):
                        calories_value = payload.get("calories")
                        if calories_value is not None:
                            update_sensor(("calories", calories_value), from_mqtt=True)
                
                # Handle standard vitals (spo2, bpm, perfusion, etc.)
                else:
                    value = payload.get(matching_vital)
                    if value is not None:
                        update_sensor((matching_vital, value), from_mqtt=True)
                    else:
                        logger.warning(f"{matching_vital} not found in payload {payload}")
                    
            except json.JSONDecodeError:
                logger.error(f"Failed to decode JSON: {msg.payload}")
            except Exception as e:
                logger.error(f"Error processing message on {msg.topic}: {e}")
        else:
            logger.warning(f"Received message for unknown topic: {msg.topic}")

    client.on_connect = on_connect
    client.on_message = on_message

    return client
