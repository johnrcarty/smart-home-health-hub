# modules/mqtt_module.py
"""
MQTT module - manages MQTT connections and publishes sensor data events from MQTT messages.
"""
import asyncio
import json
from datetime import datetime
from typing import Optional, Dict, Any
import logging

from bus import EventBus
from events import SensorUpdate, MQTTConnectionEvent, VitalSignRecorded, EventSource

logger = logging.getLogger("mqtt_module")

class MQTTModule:
    """Manages MQTT message handling and publishes events from MQTT data."""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.mqtt_manager = None
        self.mqtt_publisher = None
        self.is_connected = False
        
    def set_mqtt_components(self, mqtt_manager, mqtt_publisher):
        """Set the MQTT manager and publisher components."""
        self.mqtt_manager = mqtt_manager
        self.mqtt_publisher = mqtt_publisher
        
    async def start_event_subscribers(self):
        """Start subscribing to relevant events."""
        # Subscribe to vital_saved events to publish manually entered vitals to MQTT
        asyncio.create_task(self._subscribe_to_vital_saved())
        logger.info("MQTT module event subscribers started")
        
    async def _subscribe_to_vital_saved(self):
        """Subscribe to vital_saved events and publish them to MQTT."""
        logger.info("Starting subscription to vital_saved events")
        async for event in self.event_bus.subscribe_to_topic("vital_saved"):
            try:
                logger.info(f"Received vital_saved event: {event}")
                await self._handle_vital_saved(event)
            except Exception as e:
                logger.error(f"Error handling vital_saved event: {e}")
                
    async def _handle_vital_saved(self, event: dict):
        """Handle vital_saved events by publishing to MQTT."""
        try:
            logger.info(f"Processing vital_saved event: {event}")
            vital_type = event.get("data", {}).get("vital_type")
            vital_data = event.get("data", {}).get("vital_data", {})
            from_manual = event.get("data", {}).get("from_manual", False)
            
            logger.info(f"Extracted: vital_type={vital_type}, vital_data={vital_data}, from_manual={from_manual}")
            
            if vital_type and vital_data and from_manual:
                logger.info(f"Publishing manually saved {vital_type} to MQTT: {vital_data}")
                
                # Use the publisher to send to MQTT
                if self.mqtt_publisher and self.mqtt_publisher.is_available():
                    success = self.mqtt_publisher.publish_vital_data(vital_type, vital_data)
                    if success:
                        logger.info(f"Successfully published {vital_type} to MQTT")
                    else:
                        logger.warning(f"Failed to publish {vital_type} to MQTT")
                else:
                    logger.info(f"MQTT publisher not available for {vital_type} (MQTT disabled)")
            else:
                logger.info(f"Skipping MQTT publish - vital_type={vital_type}, has_data={bool(vital_data)}, from_manual={from_manual}")
                    
        except Exception as e:
            logger.error(f"Error handling vital_saved event: {e}")
        
    async def handle_mqtt_message(self, topic: str, payload: dict, raw_data: str):
        """
        Handle incoming MQTT messages and convert them to events.
        This replaces the direct update_sensor calls with event publishing.
        """
        try:
            # Parse topic to determine vital type
            # Expected format: shh/{vital_type}/set
            topic_parts = topic.split('/')
            if len(topic_parts) >= 2:
                vital_type = topic_parts[1]
            else:
                logger.warning(f"Invalid MQTT topic format: {topic}")
                return
            
            logger.info(f"Processing MQTT message for {vital_type}: {payload}")
            
            # Handle different vital types
            if vital_type == "blood_pressure" or vital_type == "bp":
                await self._handle_blood_pressure_mqtt(vital_type, payload, raw_data)
            elif vital_type == "temperature" or vital_type == "temp":
                await self._handle_temperature_mqtt(vital_type, payload, raw_data)
            elif vital_type in ["bathroom", "water", "calories"]:
                await self._handle_simple_vital_mqtt(vital_type, payload, raw_data)
            elif vital_type in ["spo2", "bpm", "perfusion"]:
                await self._handle_pulse_ox_mqtt(vital_type, payload, raw_data)
            else:
                # Generic vital handling
                await self._handle_generic_vital_mqtt(vital_type, payload, raw_data)
                
        except Exception as e:
            logger.error(f"Error handling MQTT message for topic {topic}: {e}")

    async def _handle_blood_pressure_mqtt(self, vital_type: str, payload: dict, raw_data: str):
        """Handle blood pressure MQTT messages."""
        systolic = payload.get("systolic")
        diastolic = payload.get("diastolic")
        map_value = payload.get("map")
        
        # Save to database if we have valid values
        if (systolic is not None and diastolic is not None and map_value is not None and
            not (systolic == 0 and diastolic == 0 and map_value == 0)):
            
            # Publish vital sign recorded event
            vital_event = VitalSignRecorded(
                ts=datetime.now(),
                vital_type="blood_pressure",
                data={
                    "systolic": systolic,
                    "diastolic": diastolic,
                    "map": map_value,
                    "raw_data": raw_data
                },
                source=EventSource.MQTT
            )
            await self.event_bus.publish(vital_event, topic="vitals.recorded")
            
            # Also publish sensor update for real-time display
            sensor_values = {
                "systolic_bp": systolic,
                "diastolic_bp": diastolic,
                "map_bp": map_value
            }
            
            sensor_event = SensorUpdate(
                ts=datetime.now(),
                values=sensor_values,
                raw=raw_data,
                source=EventSource.MQTT
            )
            await self.event_bus.publish(sensor_event, topic="sensors.update")

    async def _handle_temperature_mqtt(self, vital_type: str, payload: dict, raw_data: str):
        """Handle temperature MQTT messages."""
        skin_temp = payload.get("skin_temp")
        body_temp = payload.get("body_temp")
        
        # Save to database if we have valid values
        if skin_temp is not None and body_temp is not None:
            # Publish vital sign recorded event
            vital_event = VitalSignRecorded(
                ts=datetime.now(),
                vital_type="temperature",
                data={
                    "skin_temp": skin_temp,
                    "body_temp": body_temp,
                    "raw_data": raw_data
                },
                source=EventSource.MQTT
            )
            await self.event_bus.publish(vital_event, topic="vitals.recorded")
            
            # Also publish sensor updates for real-time display
            sensor_values = {}
            if skin_temp is not None:
                sensor_values["skin_temp"] = skin_temp
            if body_temp is not None:
                sensor_values["body_temp"] = body_temp
            
            if sensor_values:
                sensor_event = SensorUpdate(
                    ts=datetime.now(),
                    values=sensor_values,
                    raw=raw_data,
                    source=EventSource.MQTT
                )
                await self.event_bus.publish(sensor_event, topic="sensors.update")

    async def _handle_simple_vital_mqtt(self, vital_type: str, payload: dict, raw_data: str):
        """Handle simple vital signs (bathroom, water, calories)."""
        value = payload.get("value")
        
        if value is not None:
            # Publish sensor update
            sensor_values = {vital_type: value}
            
            sensor_event = SensorUpdate(
                ts=datetime.now(),
                values=sensor_values,
                raw=raw_data,
                source=EventSource.MQTT
            )
            await self.event_bus.publish(sensor_event, topic="sensors.update")

    async def _handle_pulse_ox_mqtt(self, vital_type: str, payload: dict, raw_data: str):
        """Handle pulse oximeter MQTT messages."""
        value = payload.get("value")
        
        if value is not None:
            # Publish sensor update
            sensor_values = {vital_type: value}
            
            sensor_event = SensorUpdate(
                ts=datetime.now(),
                values=sensor_values,
                raw=raw_data,
                source=EventSource.MQTT
            )
            await self.event_bus.publish(sensor_event, topic="sensors.update")

    async def _handle_generic_vital_mqtt(self, vital_type: str, payload: dict, raw_data: str):
        """Handle generic vital signs."""
        value = payload.get("value")
        
        if value is not None:
            # Publish sensor update
            sensor_values = {vital_type: value}
            
            sensor_event = SensorUpdate(
                ts=datetime.now(),
                values=sensor_values,
                raw=raw_data,
                source=EventSource.MQTT
            )
            await self.event_bus.publish(sensor_event, topic="sensors.update")

    async def publish_sensor_data_to_mqtt(self, sensor_data: dict):
        """
        Publish sensor data to MQTT topics.
        This is called when sensor data needs to be published to MQTT.
        """
        if not self.mqtt_publisher or not self.mqtt_publisher.is_available():
            logger.debug("MQTT publisher not available for publishing sensor data")
            return
            
        try:
            # Publish each sensor value to its respective MQTT topic
            for sensor_name, value in sensor_data.items():
                if value is not None:
                    topic = f"shh/{sensor_name}/state"
                    payload = {"value": value, "timestamp": datetime.now().isoformat()}
                    
                    await self.mqtt_publisher.publish_data(topic, payload)
                    logger.debug(f"Published {sensor_name}={value} to MQTT topic {topic}")
                    
        except Exception as e:
            logger.error(f"Error publishing sensor data to MQTT: {e}")

    async def publish_vital_to_mqtt(self, vital_type: str, vital_data: dict):
        """
        Publish a specific vital to MQTT.
        This is called when vitals are manually entered through the API.
        """
        if not self.mqtt_publisher or not self.mqtt_publisher.is_available():
            logger.debug("MQTT publisher not available for publishing vital")
            return
            
        try:
            topic = f"shh/{vital_type}/state"
            payload = {
                **vital_data,
                "timestamp": datetime.now().isoformat()
            }
            
            await self.mqtt_publisher.publish_data(topic, payload)
            logger.info(f"Published {vital_type} vital to MQTT topic {topic}")
            
        except Exception as e:
            logger.error(f"Error publishing vital {vital_type} to MQTT: {e}")

    async def handle_connection_status(self, connected: bool, broker: str = None, error: str = None):
        """Handle MQTT connection status changes."""
        self.is_connected = connected
        
        # Publish connection event
        event = MQTTConnectionEvent(
            ts=datetime.now(),
            connected=connected,
            broker=broker,
            error=error,
            source=EventSource.MQTT
        )
        await self.event_bus.publish(event, topic="mqtt.connection")
        
        if connected:
            logger.info(f"MQTT connected to {broker}")
        else:
            logger.warning(f"MQTT disconnected from {broker}: {error}")

    def get_status(self) -> dict:
        """Get current status of the MQTT module."""
        return {
            "connected": self.is_connected,
            "manager_available": self.mqtt_manager is not None,
            "publisher_available": self.mqtt_publisher is not None and self.mqtt_publisher.is_available()
        }
