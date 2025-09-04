"""
MQTT Client and Manager - Handles MQTT connections and message handling
"""
import json
import logging
import paho.mqtt.client as mqtt
from typing import Optional, Callable, Dict, Any
from .settings import get_mqtt_settings, get_enabled_topics

logger = logging.getLogger('mqtt.client')

class MQTTManager:
    """Manages MQTT client lifecycle and message handling"""
    
    def __init__(self, loop=None):
        self.loop = loop
        self.client: Optional[mqtt.Client] = None
        self.settings: Dict[str, Any] = {}
        self.message_handlers: Dict[str, Callable] = {}
        
    def set_message_handler(self, vital_type: str, handler: Callable):
        """Register a message handler for a specific vital type"""
        self.message_handlers[vital_type] = handler
        
    def create_client(self) -> Optional[mqtt.Client]:
        """Create and configure MQTT client with database settings"""
        self.settings = get_mqtt_settings()
        
        # Don't create client if MQTT is disabled
        if not self.settings['enabled'] or not self.settings['broker']:
            logger.info("MQTT disabled or no broker configured")
            return None
            
        self.client = mqtt.Client(client_id=self.settings['client_id'])

        if self.settings['username'] and self.settings['password']:
            self.client.username_pw_set(self.settings['username'], self.settings['password'])

        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        
        return self.client
        
    def connect(self) -> bool:
        """Connect to MQTT broker"""
        if not self.client or not self.settings.get('broker'):
            logger.error("No MQTT client or broker configured")
            return False
            
        try:
            self.client.connect(self.settings['broker'], self.settings['port'], 60)
            self.client.loop_start()
            logger.info(f"Connecting to MQTT broker at {self.settings['broker']}:{self.settings['port']}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            return False
            
    def disconnect(self):
        """Disconnect from MQTT broker"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("Disconnected from MQTT broker")
            
    def _on_connect(self, client, userdata, flags, rc):
        """Handle MQTT connection"""
        if rc == 0:
            logger.info(f"Connected to MQTT Broker at {self.settings['broker']}:{self.settings['port']}")
            
            # Subscribe to all enabled listen topics
            enabled_topics = get_enabled_topics(self.settings)
            for topic_name, topic_path in enabled_topics.items():
                # SUBSCRIBE TO LISTEN TOPICS, NOT BROADCAST/STATE
                if topic_path and 'listen' in topic_name:
                    client.subscribe(topic_path)
                    logger.info(f"Subscribed to {topic_path}")
        else:
            logger.error(f"Failed to connect to MQTT Broker, code {rc}")

    def _on_disconnect(self, client, userdata, rc):
        """Handle MQTT disconnection"""
        if rc != 0:
            logger.warning("Unexpected MQTT disconnection")
        else:
            logger.info("MQTT client disconnected")

    def _on_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        raw_data = msg.payload.decode()
        logger.info(f"MQTT Message received on {msg.topic}: {raw_data}")
        
        # Find which vital this topic belongs to
        matching_vital = self._find_matching_vital(msg.topic)
        
        if matching_vital and matching_vital in self.message_handlers:
            try:
                payload = json.loads(raw_data)
                
                # Ignore messages that originated from this client to prevent loops
                if payload.get('origin') == self.settings['client_id']:
                    logger.info(f"Ignoring message from our own client: {msg.topic}")
                    return
                
                # Call the registered handler
                self.message_handlers[matching_vital](matching_vital, payload, msg.topic, raw_data)
                    
            except json.JSONDecodeError:
                logger.error(f"Failed to decode JSON: {msg.payload}")
            except Exception as e:
                logger.error(f"Error processing message on {msg.topic}: {e}")
        else:
            logger.warning(f"Received message for unknown or unhandled topic: {msg.topic}")
            
    def _find_matching_vital(self, topic: str) -> Optional[str]:
        """Find which vital type matches the given topic"""
        for vital_name, config in self.settings.get('topics', {}).items():
            if not config.get('enabled', False):
                continue
                
            if vital_name == 'nutrition':
                if (topic == config.get('water_listen_topic') or 
                    topic == config.get('calories_listen_topic')):
                    return vital_name
            else:
                if topic == config.get('listen_topic'):
                    return vital_name
                    
        return None

def get_mqtt_client(loop=None, message_handlers: Optional[Dict[str, Callable]] = None) -> Optional[mqtt.Client]:
    """
    Create and configure MQTT client with database settings (legacy function)
    
    Args:
        loop: asyncio event loop
        message_handlers: Dict of vital_type -> handler function
        
    Returns:
        Configured MQTT client or None if disabled
    """
    manager = MQTTManager(loop)
    
    # Register message handlers if provided
    if message_handlers:
        for vital_type, handler in message_handlers.items():
            manager.set_message_handler(vital_type, handler)
    
    client = manager.create_client()
    if client:
        manager.connect()
        
    return client
