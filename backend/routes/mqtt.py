"""
MQTT configuration and management routes
"""
import logging
import time
import os
from fastapi import APIRouter, Depends, Body
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from db import get_db
from crud import get_setting, save_setting
from mqtt import send_mqtt_discovery

logger = logging.getLogger("app")

router = APIRouter(prefix="/api/mqtt", tags=["mqtt"])


def get_default_mqtt_topics():
    """Get default MQTT topic configuration"""
    return {
        'spo2': {
            'enabled': True,
            'broadcast_topic': 'shh/spo2/state',
            'listen_topic': 'shh/spo2/set'
        },
        'bpm': {
            'enabled': True,
            'broadcast_topic': 'shh/bpm/state',
            'listen_topic': 'shh/bpm/set'
        },
        'perfusion': {
            'enabled': True,
            'broadcast_topic': 'shh/perfusion/state',
            'listen_topic': 'shh/perfusion/set'
        },
        'blood_pressure': {
            'enabled': True,
            'broadcast_topic': 'shh/bp/state',
            'listen_topic': 'shh/bp/set'
        },
        'temperature': {
            'enabled': True,
            'broadcast_topic': 'shh/temp/state',
            'listen_topic': 'shh/temp/set'
        },
        'nutrition': {
            'enabled': False,
            'water_broadcast_topic': 'shh/water/state',
            'water_listen_topic': 'shh/water/set',
            'calories_broadcast_topic': 'shh/calories/state',
            'calories_listen_topic': 'shh/calories/set'
        },
        'weight': {
            'enabled': False,
            'broadcast_topic': 'shh/weight/state',
            'listen_topic': 'shh/weight/set'
        },
        'bathroom': {
            'enabled': False,
            'broadcast_topic': 'shh/bathroom/state',
            'listen_topic': 'shh/bathroom/set'
        },
        'spo2_alarm': {
            'enabled': True,
            'broadcast_topic': 'shh/alarms/spo2',
            'listen_topic': 'shh/alarms/spo2/set'
        },
        'bpm_alarm': {
            'enabled': True,
            'broadcast_topic': 'shh/alarms/bpm',
            'listen_topic': 'shh/alarms/bpm/set'
        },
        'alarm1': {
            'enabled': True,
            'broadcast_topic': 'shh/alarms/gpio1',
            'listen_topic': 'shh/alarms/gpio1/set'
        },
        'alarm2': {
            'enabled': True,
            'broadcast_topic': 'shh/alarms/gpio2',
            'listen_topic': 'shh/alarms/gpio2/set'
        }
    }


@router.get("/settings")
async def get_mqtt_settings(db: Session = Depends(get_db)):
    """Get current MQTT settings"""
    try:
        settings = {}
        mqtt_keys = [
            'mqtt_enabled', 'mqtt_broker', 'mqtt_port', 'mqtt_username', 
            'mqtt_password', 'mqtt_client_id', 'mqtt_discovery_enabled', 
            'mqtt_test_mode', 'mqtt_base_topic'
        ]
        
        for key in mqtt_keys:
            settings[key] = get_setting(db, key)
        
        # Load topic configurations
        topics_setting = get_setting(db, 'mqtt_topics')
        default_topics = get_default_mqtt_topics()
        merged_topics = default_topics.copy()
        if topics_setting is not None:
            import json
            try:
                saved_topics = json.loads(topics_setting) if isinstance(topics_setting, str) else topics_setting
                merged_topics.update(saved_topics)
            except (json.JSONDecodeError, TypeError):
                pass
        settings['topics'] = merged_topics
        
        return settings
    except Exception as e:
        logger.error(f"Error getting MQTT settings: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error retrieving MQTT settings: {str(e)}"}
        )


@router.post("/settings")
async def save_mqtt_settings(settings: dict, db: Session = Depends(get_db)):
    """Save MQTT settings"""
    try:
        # Save basic MQTT settings with proper data types
        for key, value in settings.items():
            if key != 'topics':  # Handle topics separately
                # Determine data type
                if key in ['mqtt_enabled', 'mqtt_discovery_enabled', 'mqtt_test_mode']:
                    data_type = 'bool'
                elif key == 'mqtt_port':
                    data_type = 'int'
                else:
                    data_type = 'string'
                save_setting(db, key, value, data_type)
        
        # Save topic configurations as JSON
        if 'topics' in settings:
            import json
            save_setting(db, 'mqtt_topics', json.dumps(settings['topics']), 'json')
        
        # Restart MQTT connection with new settings if MQTT is enabled
        restart_result = await restart_mqtt_if_enabled(db)
        
        return {"message": "MQTT settings saved successfully", "mqtt_restart": restart_result}
    except Exception as e:
        logger.error(f"Error saving MQTT settings: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error saving MQTT settings: {str(e)}"}
        )


async def restart_mqtt_if_enabled(db: Session):
    """Restart MQTT connection if enabled in settings"""
    # Import at function level to avoid circular imports
    import asyncio
    from main import mqtt_client_ref, mqtt_manager, mqtt_publisher, set_mqtt_publisher
    from mqtt import MQTTManager, MQTTPublisher, create_message_handlers
    from state_manager import update_sensor
    
    try:
        # Check if MQTT is enabled
        from mqtt.settings import is_mqtt_enabled
        
        if not is_mqtt_enabled():
            # Disconnect existing client if any
            if mqtt_client_ref and hasattr(mqtt_manager, 'disconnect'):
                mqtt_manager.disconnect()
            return "MQTT disabled - disconnected"
        
        # Disconnect existing client
        if mqtt_client_ref and hasattr(mqtt_manager, 'disconnect'):
            try:
                mqtt_manager.disconnect()
            except:
                pass
            mqtt_client_ref = None
        
        # Create new MQTT manager and client with updated settings
        mqtt_manager = MQTTManager(asyncio.get_event_loop())
        mqtt_publisher = MQTTPublisher()
        
        # Create message handlers for incoming MQTT messages
        message_handlers = create_message_handlers(update_sensor)
        for vital_type, handler in message_handlers.items():
            mqtt_manager.set_message_handler(vital_type, handler)
        
        # Create and connect client
        mqtt_client = mqtt_manager.create_client()
        
        if mqtt_client and mqtt_manager.connect():
            logger.info("[restart_mqtt] Connected to MQTT broker")
            
            # Set up the publisher with the client
            mqtt_publisher.set_client(mqtt_client)
            
            # Send MQTT discovery if enabled
            discovery_enabled = get_setting(db, 'mqtt_discovery_enabled', True)
            test_mode = get_setting(db, 'mqtt_test_mode', True)
            
            if discovery_enabled:
                send_mqtt_discovery(mqtt_client, test_mode=test_mode)

            # Set availability to online using base topic from settings
            from mqtt.settings import get_mqtt_settings
            mqtt_settings = get_mqtt_settings()
            base_topic = mqtt_settings.get('base_topic', 'shh')
            mqtt_client.publish(f"{base_topic}/availability", "online", retain=True)
            logger.info(f"[restart_mqtt] Published online status to {base_topic}/availability")

            # Set the MQTT publisher in the state manager
            set_mqtt_publisher(mqtt_publisher)
            mqtt_client_ref = mqtt_client
            
            return "MQTT connection restarted successfully"
        else:
            return "MQTT connection failed - invalid settings"
            
    except Exception as e:
        logger.error(f"[restart_mqtt] Error restarting MQTT: {e}")
        return f"MQTT restart failed: {str(e)}"


@router.post("/test-connection")
async def test_mqtt_connection(settings: dict):
    """Test MQTT connection with provided settings"""
    try:
        import paho.mqtt.client as mqtt
        
        test_client = mqtt.Client(client_id=settings.get('mqtt_client_id', 'test_client'))
        
        # Set credentials if provided
        username = settings.get('mqtt_username')
        password = settings.get('mqtt_password')
        if username and password:
            test_client.username_pw_set(username, password)
        
        connection_result = {"connected": False, "error": None}
        
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                connection_result["connected"] = True
            else:
                connection_result["error"] = f"Connection failed with code {rc}"
        
        def on_disconnect(client, userdata, rc):
            connection_result["connected"] = False
        
        test_client.on_connect = on_connect
        test_client.on_disconnect = on_disconnect
        
        # Try to connect
        broker = settings.get('mqtt_broker', 'localhost')
        port = int(settings.get('mqtt_port', 1883))
        
        test_client.connect(broker, port, 10)
        test_client.loop_start()
        
        # Wait for connection attempt
        time.sleep(2)
        test_client.loop_stop()
        
        if connection_result["connected"]:
            test_client.disconnect()
            return {"status": "success", "message": "MQTT connection successful"}
        else:
            error_msg = connection_result["error"] or "Connection failed"
            return JSONResponse(status_code=400, content={"detail": error_msg})
            
    except Exception as e:
        logger.error(f"Error testing MQTT connection: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error testing MQTT connection: {str(e)}"}
        )


@router.post("/send-discovery")
async def send_mqtt_discovery_endpoint(request: dict):
    """Send MQTT discovery messages to Home Assistant"""
    try:
        test_mode = request.get('test_mode', True)
        
        # Get the current MQTT client (if connected)
        from main import mqtt_client_ref
        if mqtt_client_ref and mqtt_client_ref.is_connected():
            send_mqtt_discovery(mqtt_client_ref, test_mode=test_mode)
            return {"message": "MQTT discovery messages sent successfully"}
        else:
            return JSONResponse(
                status_code=400,
                content={"detail": "MQTT client not connected"}
            )
            
    except Exception as e:
        logger.error(f"Error sending MQTT discovery: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error sending MQTT discovery: {str(e)}"}
        )
