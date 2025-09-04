"""
MQTT Discovery - Home Assistant MQTT Discovery functionality
"""
import json
import logging
from typing import Dict, Any, Optional
from .settings import get_mqtt_settings

logger = logging.getLogger('mqtt.discovery')

def send_mqtt_discovery(mqtt_client, test_mode: bool = True) -> bool:
    """
    Send MQTT Discovery messages to Home Assistant.
    
    Args:
        mqtt_client: The connected MQTT client
        test_mode: If True, uses {base_topic}-test instead of {base_topic}
        
    Returns:
        bool: True if discovery messages were sent successfully
    """
    if not mqtt_client or not mqtt_client.is_connected():
        logger.error("MQTT client not available for discovery")
        return False
        
    settings = get_mqtt_settings()
    if not settings['enabled']:
        logger.warning("MQTT disabled, skipping discovery")
        return False
        
    # Get base topic from database settings
    base_topic = settings.get('base_topic', 'shh')
    
    # Apply test mode suffix
    if test_mode:
        base_topic = f"{base_topic}-test"
    
    discovery_prefix = "homeassistant"
    topics_config = settings.get('topics', {})
    
    device_info = {
        "mf": "Smart Home Health",
        "mdl": "Smart Healthcare Hub",
        "name": "Medical Device Monitor",
        "ids": ["shh_medical_hub"]
    }

    sensors = {}
    
    # Generate sensors dynamically based on enabled topics
    for vital_name, config in topics_config.items():
        if not config.get('enabled', False):
            continue
        
        # Handle nutrition special case with multiple sensors
        if vital_name == 'nutrition':
            # Water sensor
            water_topic = config.get('water_broadcast_topic')
            if water_topic:
                sensors[f"{vital_name}_water"] = {
                    "uniq_id": f"{base_topic}_sensor.{vital_name}_water",
                    "name": "Water Intake",
                    "stat_t": water_topic,
                    "template_value": "{{ value_json['water'] }}",
                    "json_attr_t": f"{water_topic}/attributes",
                    "avty_t": f"{base_topic}/availability",
                    "unit_of_meas": "ml",
                    "stat_cla": "total_increasing",
                }
            
            # Calories sensor
            calories_topic = config.get('calories_broadcast_topic')
            if calories_topic:
                sensors[f"{vital_name}_calories"] = {
                    "uniq_id": f"{base_topic}_sensor.{vital_name}_calories",
                    "name": "Calorie Intake",
                    "stat_t": calories_topic,
                    "template_value": "{{ value_json['calories'] }}",
                    "json_attr_t": f"{calories_topic}/attributes",
                    "avty_t": f"{base_topic}/availability",
                    "unit_of_meas": "kcal",
                    "stat_cla": "total_increasing",
                }
        
        # Handle standard vitals
        else:
            broadcast_topic = config.get('broadcast_topic')
            if broadcast_topic:
                sensor_config = get_sensor_config(vital_name, broadcast_topic, base_topic)
                if sensor_config:
                    sensors[vital_name] = sensor_config

    
    # Send discovery messages for all configured sensors
    success_count = 0
    for sensor_id, config in sensors.items():
        config["dev"] = device_info
        discovery_topic = f"{discovery_prefix}/sensor/{sensor_id}/config"
        json_payload = json.dumps(config)

        try:
            result = mqtt_client.publish(discovery_topic, json_payload, retain=True)
            if result.rc == 0:
                logger.info(f"Sent MQTT Discovery for {sensor_id} to {discovery_topic}")
                success_count += 1
            else:
                logger.error(f"Failed to send discovery for {sensor_id}: rc={result.rc}")
        except Exception as e:
            logger.error(f"Error sending discovery for {sensor_id}: {e}")
            
    logger.info(f"Sent {success_count}/{len(sensors)} MQTT Discovery messages")
    return success_count > 0

def get_sensor_config(vital_name: str, broadcast_topic: str, base_topic: str) -> Optional[Dict[str, Any]]:
    """
    Get sensor configuration for a specific vital type
    
    Args:
        vital_name: Name of the vital (e.g., 'spo2', 'temperature')
        broadcast_topic: MQTT topic where the sensor publishes data
        base_topic: Base MQTT topic for the system
        
    Returns:
        Dict containing sensor configuration or None if not supported
    """
    vital_configs = {
        'spo2': {
            "uniq_id": f"{base_topic}_sensor.spo2",
            "name": "SpO₂ Level",
            "stat_t": broadcast_topic,
            "template_value": "{{ value_json['spo2'] }}",
            "json_attr_t": f"{broadcast_topic}/attributes",
            "avty_t": f"{base_topic}/availability",
            "unit_of_meas": "%",
            "stat_cla": "measurement",
        },
        'bpm': {
            "uniq_id": f"{base_topic}_sensor.bpm",
            "name": "Heart Rate",
            "stat_t": broadcast_topic,
            "template_value": "{{ value_json['bpm'] }}",
            "json_attr_t": f"{broadcast_topic}/attributes",
            "avty_t": f"{base_topic}/availability",
            "unit_of_meas": "BPM",
            "stat_cla": "measurement",
        },
        'perfusion': {
            "uniq_id": f"{base_topic}_sensor.perfusion",
            "name": "Perfusion Index",
            "stat_t": broadcast_topic,
            "template_value": "{{ value_json['perfusion'] }}",
            "json_attr_t": f"{broadcast_topic}/attributes",
            "avty_t": f"{base_topic}/availability",
            "unit_of_meas": "PA",
            "stat_cla": "measurement",
        },
        'blood_pressure': {
            "uniq_id": f"{base_topic}_sensor.blood_pressure",
            "name": "Blood Pressure",
            "stat_t": broadcast_topic,
            "template_value": "{{ value_json['systolic'] }}/{{ value_json['diastolic'] }} ({{ value_json['map'] }})",
            "json_attr_t": f"{broadcast_topic}/attributes",
            "avty_t": f"{base_topic}/availability",
            "unit_of_meas": "mmHg",
        },
        'temperature': {
            "uniq_id": f"{base_topic}_sensor.temperature",
            "name": "Body Temperature",
            "stat_t": broadcast_topic,
            "template_value": "{{ value_json['body_temp'] }}",
            "json_attr_t": f"{broadcast_topic}/attributes",
            "avty_t": f"{base_topic}/availability",
            "unit_of_meas": "°F",
            "stat_cla": "measurement",
        },
        'weight': {
            "uniq_id": f"{base_topic}_sensor.weight",
            "name": "Weight",
            "stat_t": broadcast_topic,
            "template_value": "{{ value_json['weight'] }}",
            "json_attr_t": f"{broadcast_topic}/attributes",
            "avty_t": f"{base_topic}/availability",
            "unit_of_meas": "lbs",
            "stat_cla": "measurement",
        },
        'bathroom': {
            "uniq_id": f"{base_topic}_sensor.bathroom",
            "name": "Bathroom Activity",
            "stat_t": broadcast_topic,
            "template_value": "{{ value_json['bathroom'] }}",
            "json_attr_t": f"{broadcast_topic}/attributes",
            "avty_t": f"{base_topic}/availability",
        },
        'spo2_alarm': {
            "uniq_id": f"{base_topic}_sensor.spo2_alarm",
            "name": "SpO₂ Alarm",
            "stat_t": broadcast_topic,
            "template_value": "{{ value_json['spo2_alarm'] }}",
            "json_attr_t": f"{broadcast_topic}/attributes",
            "avty_t": f"{base_topic}/availability",
            "payload_on": "ON",
            "payload_off": "OFF",
            "device_class": "problem",
        },
        'bpm_alarm': {
            "uniq_id": f"{base_topic}_sensor.bmp_alarm",
            "name": "Heart Rate Alarm",
            "stat_t": broadcast_topic,
            "template_value": "{{ value_json['bpm_alarm'] }}",
            "json_attr_t": f"{broadcast_topic}/attributes",
            "avty_t": f"{base_topic}/availability",
            "payload_on": "ON",
            "payload_off": "OFF",
            "device_class": "problem",
        },
        'alarm1': {
            "uniq_id": f"{base_topic}_sensor.gpio_alarm1",
            "name": "GPIO Alarm 1",
            "stat_t": broadcast_topic,
            "template_value": "{{ value_json['alarm1'] }}",
            "json_attr_t": f"{broadcast_topic}/attributes",
            "avty_t": f"{base_topic}/availability",
            "payload_on": "ON",
            "payload_off": "OFF",
            "device_class": "problem",
        },
        'alarm2': {
            "uniq_id": f"{base_topic}_sensor.gpio_alarm2",
            "name": "GPIO Alarm 2",
            "stat_t": broadcast_topic,
            "template_value": "{{ value_json['alarm2'] }}",
            "json_attr_t": f"{broadcast_topic}/attributes",
            "avty_t": f"{base_topic}/availability",
            "payload_on": "ON",
            "payload_off": "OFF",
            "device_class": "problem",
        }
    }
    
    return vital_configs.get(vital_name)
