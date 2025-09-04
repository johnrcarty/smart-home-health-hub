"""
MQTT Settings and Configuration
"""
import json
from typing import Dict, Any, Optional
from crud import get_setting
from db import get_db
import logging

logger = logging.getLogger('mqtt.settings')

def get_mqtt_settings() -> Dict[str, Any]:
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
        settings['base_topic'] = get_setting(db, 'mqtt_base_topic', 'shh')
        
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
            'base_topic': 'shh',
            'topics': {}
        }
    finally:
        db.close()

def get_enabled_topics(mqtt_settings: Dict[str, Any]) -> Dict[str, str]:
    """Get list of enabled topics from MQTT settings"""
    enabled_topics = {}
    
    for vital_name, config in mqtt_settings.get('topics', {}).items():
        if config.get('enabled', False):
            # Handle nutrition special case with 4 topics
            if vital_name == 'nutrition':
                if config.get('water_broadcast_topic'):
                    enabled_topics['water_broadcast'] = config.get('water_broadcast_topic')
                if config.get('water_listen_topic'):
                    enabled_topics['water_listen'] = config.get('water_listen_topic')
                if config.get('calories_broadcast_topic'):
                    enabled_topics['calories_broadcast'] = config.get('calories_broadcast_topic')
                if config.get('calories_listen_topic'):
                    enabled_topics['calories_listen'] = config.get('calories_listen_topic')
            else:
                # Standard vitals with broadcast and listen topics
                if config.get('broadcast_topic'):
                    enabled_topics[f'{vital_name}_broadcast'] = config['broadcast_topic']
                if config.get('listen_topic'):
                    enabled_topics[f'{vital_name}_listen'] = config['listen_topic']
    
    return enabled_topics

def is_mqtt_enabled() -> bool:
    """Quick check if MQTT is enabled"""
    settings = get_mqtt_settings()
    return settings.get('enabled', False) and settings.get('broker', '')

def get_vital_topic_config(vital_type: str) -> Optional[Dict[str, Any]]:
    """Get topic configuration for a specific vital type"""
    settings = get_mqtt_settings()
    if not settings.get('enabled', False):
        return None
        
    topics = settings.get('topics', {})
    vital_config = topics.get(vital_type, {})
    
    if not vital_config.get('enabled', False):
        return None
        
    return vital_config
