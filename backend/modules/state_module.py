# modules/state_module.py
"""
State module - manages centralized application state and handles database operations.
"""
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
import logging

from bus import EventBus
from events import (
    SensorUpdate, VitalSignRecorded, AlertTriggered, AlertResolved, 
    MedicationDue, CareTaskDue, EventSource
)

logger = logging.getLogger("state_module")

class StateModule:
    """Manages centralized application state and database operations."""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        
        # Current sensor state
        self.sensor_state = {}
        
        # Initialize with default sensor values
        self._initialize_sensor_state()
        
        # Alert tracking
        self.current_alert_id = None
        self.alert_thresholds_exceeded = False
        self.alert_start_data_id = None
        self.alert_recovery_start_time = None
        
        # Pulse ox data caching for alerts
        self.pulse_ox_cache = []
        self.event_data_points = []
        
    def _initialize_sensor_state(self):
        """Initialize sensor state with default values."""
        from sensor_manager import SENSOR_DEFINITIONS
        
        self.sensor_state = {name: None for name in SENSOR_DEFINITIONS.keys()}
        logger.info("Sensor state initialized")

    async def start_event_subscribers(self):
        """Start subscribing to relevant events."""
        # Subscribe to sensor updates
        asyncio.create_task(self._subscribe_to_sensor_updates())
        
        # Subscribe to vital recordings
        asyncio.create_task(self._subscribe_to_vital_recordings())
        
        logger.info("State module event subscribers started")

    async def _subscribe_to_sensor_updates(self):
        """Subscribe to sensor update events and maintain state."""
        async for event in self.event_bus.subscribe_to_type(SensorUpdate):
            try:
                await self._handle_sensor_update(event)
            except Exception as e:
                logger.error(f"Error handling sensor update: {e}")

    async def _subscribe_to_vital_recordings(self):
        """Subscribe to vital recording events and save to database."""
        async for event in self.event_bus.subscribe_to_type(VitalSignRecorded):
            try:
                await self._handle_vital_recording(event)
            except Exception as e:
                logger.error(f"Error handling vital recording: {e}")

    async def _handle_sensor_update(self, event: SensorUpdate):
        """Handle sensor update events."""
        # Update local state
        self.sensor_state.update(event.values)
        
        logger.debug(f"Updated sensor state: {event.values}")
        
        # Check for alerts if this is pulse ox data
        pulse_ox_values = {}
        for key in ["spo2", "bpm", "perfusion"]:
            if key in event.values:
                pulse_ox_values[key] = event.values[key]
        
        if pulse_ox_values:
            await self._handle_pulse_ox_update(pulse_ox_values, event.raw)
        
        # Publish to MQTT if this didn't originate from MQTT
        if event.source != EventSource.MQTT:
            await self._publish_sensor_data_to_mqtt(event.values)

    async def _handle_vital_recording(self, event: VitalSignRecorded):
        """Handle vital recording events by saving to database."""
        try:
            from state_manager import get_db_session
            
            # Check if unified storage should be used
            use_unified = event.data.get("use_unified_storage", False)
            
            if event.vital_type == "blood_pressure":
                if use_unified:
                    from crud.vitals import save_blood_pressure_as_vitals
                    with get_db_session() as db:
                        save_blood_pressure_as_vitals(
                            db=db,
                            systolic=event.data["systolic"],
                            diastolic=event.data["diastolic"],
                            map_value=event.data["map"],
                            notes=event.data.get("raw_data")
                        )
                    logger.info(f"Saved blood pressure reading to unified vitals table")
                else:
                    from crud.vitals import save_blood_pressure
                    with get_db_session() as db:
                        save_blood_pressure(
                            db=db,
                            systolic=event.data["systolic"],
                            diastolic=event.data["diastolic"],
                            map_value=event.data["map"],
                            raw_data=event.data.get("raw_data")
                        )
                    logger.info(f"Saved blood pressure reading to database")
                
            elif event.vital_type == "temperature":
                if use_unified:
                    from crud.vitals import save_temperature_as_vitals
                    with get_db_session() as db:
                        save_temperature_as_vitals(
                            db=db,
                            body_temp=event.data["body_temp"],
                            skin_temp=event.data.get("skin_temp"),
                            notes=event.data.get("raw_data")
                        )
                    logger.info(f"Saved temperature reading to unified vitals table")
                else:
                    from crud.vitals import save_temperature
                    with get_db_session() as db:
                        save_temperature(
                            db=db,
                            skin_temp=event.data["skin_temp"],
                            body_temp=event.data["body_temp"],
                            raw_data=event.data.get("raw_data")
                        )
                    logger.info(f"Saved temperature reading to database")
                
        except Exception as e:
            logger.error(f"Error saving vital recording to database: {e}")

    async def _handle_pulse_ox_update(self, pulse_ox_data: dict, raw_data: Optional[str]):
        """Handle pulse oximeter data and check for alerts."""
        try:
            spo2 = pulse_ox_data.get("spo2")
            bpm = pulse_ox_data.get("bpm") 
            perfusion = pulse_ox_data.get("perfusion")
            
            # Cache the data
            timestamp = datetime.now()
            data_point = {
                "timestamp": timestamp,
                "spo2": spo2,
                "bpm": bpm,
                "perfusion": perfusion,
                "raw": raw_data
            }
            
            self.pulse_ox_cache.append(data_point)
            
            # Keep only last 150 points (~30 seconds at 5Hz)
            if len(self.pulse_ox_cache) > 150:
                self.pulse_ox_cache.pop(0)
            
            # Save to database
            await self._save_pulse_ox_data(spo2, bpm, perfusion, raw_data)
            
            # Check thresholds for alerts
            await self._check_pulse_ox_thresholds(spo2, bpm, timestamp, data_point)
            
        except Exception as e:
            logger.error(f"Error handling pulse ox update: {e}")

    async def _save_pulse_ox_data(self, spo2, bpm, perfusion, raw_data):
        """Save pulse oximeter data to database."""
        try:
            from state_manager import get_db_session
            from crud.vitals import save_pulse_ox_data
            
            with get_db_session() as db:
                save_pulse_ox_data(
                    db=db,
                    spo2=spo2,
                    bpm=bpm,
                    pa=perfusion,  # Fixed: pa parameter instead of perfusion
                    raw_data=raw_data
                )
                
        except Exception as e:
            logger.error(f"Error saving pulse ox data: {e}")

    async def _check_pulse_ox_thresholds(self, spo2, bpm, timestamp, data_point):
        """Check pulse ox values against thresholds and manage alerts."""
        try:
            from crud.settings import get_setting
            from state_manager import get_db_session
            
            with get_db_session() as db:
                min_spo2 = int(get_setting(db, 'min_spo2', 90))
                max_spo2 = int(get_setting(db, 'max_spo2', 100))
                min_bpm = int(get_setting(db, 'min_bpm', 55))
                max_bpm = int(get_setting(db, 'max_bpm', 155))
            
            # Check if device is disconnected (timeout values)
            is_disconnected = (spo2 == -1) or (bpm == -1)
            
            # Check if thresholds are exceeded (only for valid data)
            spo2_alarm = False
            bpm_alarm = False
            
            if not is_disconnected:
                if spo2 is not None:
                    spo2_alarm = spo2 < min_spo2 or spo2 > max_spo2
                
                if bpm is not None:
                    bpm_alarm = bpm < min_bpm or bpm > max_bpm
            
            current_thresholds_exceeded = spo2_alarm or bpm_alarm
            currently_disconnected = is_disconnected
            
            # Handle disconnection alerts differently from threshold alerts
            if currently_disconnected and not self.alert_thresholds_exceeded:
                # Device just disconnected - start a disconnection alert
                await self._start_pulse_ox_alert(spo2, bpm, timestamp, data_point, alert_type="disconnected")
                
            elif not currently_disconnected and self.alert_thresholds_exceeded and self.current_alert_id:
                # Device reconnected - check if previous alert was disconnection
                # End the disconnection alert immediately since we have real data
                await self._end_pulse_ox_alert(timestamp)
                
                # Now check if the new data triggers threshold alerts
                if current_thresholds_exceeded:
                    await self._start_pulse_ox_alert(spo2, bpm, timestamp, data_point, alert_type="threshold")
                    
            elif current_thresholds_exceeded and not self.alert_thresholds_exceeded and not currently_disconnected:
                # Normal threshold alert started (device connected but values out of range)
                await self._start_pulse_ox_alert(spo2, bpm, timestamp, data_point, alert_type="threshold")
                
            elif not current_thresholds_exceeded and self.alert_thresholds_exceeded and not currently_disconnected:
                # Threshold alert condition cleared - start recovery timer
                self.alert_recovery_start_time = timestamp
                
            elif not current_thresholds_exceeded and self.alert_recovery_start_time and not currently_disconnected:
                # Check if recovery period has elapsed (only for threshold alerts)
                recovery_duration = (timestamp - self.alert_recovery_start_time).total_seconds()
                if recovery_duration >= 30:  # 30 second recovery period
                    await self._end_pulse_ox_alert(timestamp)
            
            # Update state - track both disconnection and threshold states
            self.alert_thresholds_exceeded = current_thresholds_exceeded or currently_disconnected
            
            # Add to event data if we're tracking an alert
            if self.current_alert_id:
                self.event_data_points.append(data_point)
                
        except Exception as e:
            logger.error(f"Error checking pulse ox thresholds: {e}")

    async def _start_pulse_ox_alert(self, spo2, bpm, timestamp, data_point, alert_type="threshold"):
        """Start a new pulse oximeter alert."""
        try:
            from state_manager import get_db_session
            from crud.monitoring import start_monitoring_alert
            
            # Determine alert flags based on alert type
            if alert_type == "disconnected":
                # For disconnection alerts, mark as device disconnected
                spo2_alarm = False  # Don't treat -1 as threshold violation
                hr_alarm = False
                external_alarm_triggered = 1  # Use external alarm flag for disconnection
            else:
                # For threshold alerts, use normal logic
                spo2_alarm = spo2 and (spo2 < 85 or spo2 > 100) if spo2 and spo2 != -1 else False
                hr_alarm = bpm and (bpm < 50 or bpm > 160) if bpm and bpm != -1 else False
                external_alarm_triggered = 0
            
            with get_db_session() as db:
                alert_data = start_monitoring_alert(
                    db=db,
                    spo2=spo2,
                    bpm=bpm,
                    data_id=data_point.get("id"),  # If you track data point IDs
                    spo2_alarm_triggered=1 if spo2_alarm else 0,
                    hr_alarm_triggered=1 if hr_alarm else 0,
                    external_alarm_triggered=external_alarm_triggered
                )
                if alert_data:
                    self.current_alert_id = alert_data.id if hasattr(alert_data, 'id') else alert_data
                    self.alert_start_data_id = data_point.get("id")
            
            # Reset event tracking
            self.event_data_points = list(self.pulse_ox_cache)  # Copy current cache
            self.alert_recovery_start_time = None
            
            # Determine severity based on alert type
            if alert_type == "disconnected":
                severity = "medium"
                alert_description = f"Device disconnected (SpO2={spo2}, BPM={bpm})"
            else:
                severity = "high" if spo2_alarm or hr_alarm else "medium"
                alert_description = f"Threshold violation (SpO2={spo2}, BPM={bpm})"
            
            # Publish alert triggered event
            alert_event = AlertTriggered(
                ts=timestamp,
                alert_type=f"pulse_ox_{alert_type}",
                alert_data={"spo2": spo2, "bpm": bpm, "timestamp": timestamp.isoformat(), "type": alert_type},
                severity=severity,
                source=EventSource.SYSTEM
            )
            await self.event_bus.publish(alert_event, topic="alerts.triggered")
            
            logger.warning(f"Pulse ox {alert_type} alert started: {alert_description}")
            
        except Exception as e:
            logger.error(f"Error starting pulse ox alert: {e}")

    async def _end_pulse_ox_alert(self, timestamp):
        """End the current pulse oximeter alert."""
        try:
            from state_manager import get_db_session
            from crud.monitoring import update_monitoring_alert
            
            if self.current_alert_id:
                with get_db_session() as db:
                    update_monitoring_alert(
                        db=db,
                        alert_id=self.current_alert_id,
                        acknowledged=True,
                        notes="Automatically resolved after recovery period"
                    )
                
                # Publish alert resolved event
                alert_event = AlertResolved(
                    ts=timestamp,
                    alert_id=self.current_alert_id,
                    resolution_type="automatic",
                    source=EventSource.SYSTEM
                )
                await self.event_bus.publish(alert_event, topic="alerts.resolved")
                
                logger.info(f"Pulse ox alert {self.current_alert_id} automatically resolved")
                
                # Reset tracking
                self.current_alert_id = None
                self.alert_start_data_id = None
                self.event_data_points = []
                
            self.alert_recovery_start_time = None
            
        except Exception as e:
            logger.error(f"Error ending pulse ox alert: {e}")

    async def _publish_sensor_data_to_mqtt(self, sensor_data: dict):
        """Publish sensor data to MQTT via MQTT module."""
        # This would typically trigger an event that the MQTT module subscribes to
        # For now, we'll use a direct call pattern
        try:
            # We could publish a "MQTTPublishRequest" event instead
            from modules.mqtt_module import MQTTModule
            # This is not ideal - better to use event bus for this too
            pass  # TODO: Implement proper event-based MQTT publishing
            
        except Exception as e:
            logger.error(f"Error publishing to MQTT: {e}")

    def get_current_state(self) -> dict:
        """Get the current sensor state."""
        return self.sensor_state.copy()

    def get_status(self) -> dict:
        """Get current status of the state module."""
        return {
            "sensor_count": len(self.sensor_state),
            "current_alert_id": self.current_alert_id,
            "alert_active": self.current_alert_id is not None,
            "thresholds_exceeded": self.alert_thresholds_exceeded,
            "cache_size": len(self.pulse_ox_cache)
        }
