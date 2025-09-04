# modules/gpio_module.py
"""
GPIO monitoring module - manages GPIO pin monitoring and publishes alarm state events.
"""
import asyncio
import time
import threading
from datetime import datetime
from typing import Dict, Optional
import logging

from bus import EventBus
from events import AlarmPanelState, EventSource

logger = logging.getLogger("gpio_module")

# Try to import GPIO library
try:
    import lgpio
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    logger.warning("lgpio not available - GPIO functionality disabled")

class GPIOModule:
    """Manages GPIO pin monitoring and publishes alarm state events."""
    
    def __init__(self, event_bus: EventBus, loop: asyncio.AbstractEventLoop):
        self.event_bus = event_bus
        self.loop = loop
        self.is_running = False
        self.lgpio_handle: Optional[int] = None
        
        # Default GPIO pin mappings
        self.gpio_map = {
            "alarm1": [17, 18, 27, 22],
            "alarm2": [5, 6, 13, 19],
        }
        
        # Current alarm states
        self.alarm_states = {"alarm1": False, "alarm2": False}
        
        # Device settings cache
        self.device_settings = {
            "alarm1": {"device_type": "vent", "recovery_time": 30},
            "alarm2": {"device_type": "pulseox", "recovery_time": 30}
        }
        
        # Tracking for alarm recovery
        self.device_triggered = {}
        self.device_last_trigger_time = {}
        self.device_recovery_time = {}
        
        # Worker thread for GPIO monitoring
        self.gpio_thread: Optional[threading.Thread] = None

    def get_device_settings(self) -> dict:
        """Get device settings from database."""
        try:
            from crud.settings import get_setting
            from db import get_db
            
            db = next(get_db())
            try:
                alarm1_device = get_setting(db, "alarm1_device", "vent")
                alarm2_device = get_setting(db, "alarm2_device", "pulseox")
                alarm1_recovery = int(get_setting(db, "alarm1_recovery_time", 30))
                alarm2_recovery = int(get_setting(db, "alarm2_recovery_time", 30))
                
                settings = {
                    "alarm1": {"device_type": alarm1_device, "recovery_time": alarm1_recovery},
                    "alarm2": {"device_type": alarm2_device, "recovery_time": alarm2_recovery}
                }
                
                self.device_settings = settings
                return settings
                
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error getting device settings: {e}")
            return self.device_settings

    def publish_alarm_state(self):
        """Publish current alarm state as an event."""
        event = AlarmPanelState(
            ts=datetime.now(),
            alarm1=self.alarm_states["alarm1"],
            alarm2=self.alarm_states["alarm2"],
            source=EventSource.GPIO
        )
        
        # Use thread-safe call to publish from the GPIO thread
        future = asyncio.run_coroutine_threadsafe(
            self.event_bus.publish(event, topic="gpio.alarms"),
            self.loop
        )
        try:
            future.result(timeout=1.0)
        except Exception as e:
            logger.error(f"Failed to publish alarm state: {e}")

    def gpio_callback(self, gpio: int, level: int, tick: int):
        """Callback for GPIO edge detection."""
        current_time = time.time()
        device_settings = self.get_device_settings()
        
        # Determine which alarm this GPIO belongs to
        alarm_key = None
        for key, pins in self.gpio_map.items():
            if gpio in pins:
                alarm_key = key
                break
        
        if not alarm_key:
            logger.warning(f"GPIO {gpio} not mapped to any alarm")
            return
        
        device_type = device_settings[alarm_key]["device_type"]
        recovery_time = device_settings[alarm_key]["recovery_time"]
        
        logger.info(f"GPIO {gpio} ({alarm_key}, {device_type}) triggered with level {level}")
        
        # Level 0 = alarm active (pulled low), Level 1 = alarm inactive (pulled high)
        alarm_active = (level == 0)
        
        if alarm_active:
            # Alarm triggered
            self.device_triggered[alarm_key] = True
            self.device_last_trigger_time[alarm_key] = current_time
            self.device_recovery_time[alarm_key] = recovery_time
            
            if not self.alarm_states[alarm_key]:
                self.alarm_states[alarm_key] = True
                logger.warning(f"ALARM TRIGGERED: {alarm_key} ({device_type})")
                self.publish_alarm_state()
        else:
            # Alarm signal cleared - start recovery timer
            if alarm_key in self.device_triggered and self.device_triggered[alarm_key]:
                logger.info(f"Alarm signal cleared for {alarm_key}, starting recovery timer ({recovery_time}s)")
                self.device_triggered[alarm_key] = False

    def check_recovery_timers(self):
        """Check if any alarms should be cleared based on recovery timers."""
        current_time = time.time()
        state_changed = False
        
        for alarm_key in ["alarm1", "alarm2"]:
            if (self.alarm_states[alarm_key] and 
                alarm_key in self.device_triggered and 
                not self.device_triggered[alarm_key] and
                alarm_key in self.device_last_trigger_time and
                alarm_key in self.device_recovery_time):
                
                elapsed = current_time - self.device_last_trigger_time[alarm_key]
                recovery_time = self.device_recovery_time[alarm_key]
                
                if elapsed >= recovery_time:
                    self.alarm_states[alarm_key] = False
                    device_type = self.device_settings[alarm_key]["device_type"]
                    logger.info(f"ALARM CLEARED: {alarm_key} ({device_type}) after {recovery_time}s recovery")
                    state_changed = True
                    
                    # Clean up tracking
                    del self.device_last_trigger_time[alarm_key]
                    del self.device_recovery_time[alarm_key]
        
        if state_changed:
            self.publish_alarm_state()

    def gpio_worker(self):
        """Worker thread for GPIO monitoring."""
        if not GPIO_AVAILABLE:
            logger.error("GPIO functionality not available")
            return
            
        logger.info("GPIO worker thread started")
        
        try:
            # Open GPIO handle
            self.lgpio_handle = lgpio.gpiochip_open(0)
            logger.info(f"Opened GPIO chip with handle: {self.lgpio_handle}")
            
            # Set up GPIO pins for monitoring
            for alarm_key, pins in self.gpio_map.items():
                for pin in pins:
                    try:
                        # Set pin as input with pull-up resistor
                        lgpio.gpio_claim_input(self.lgpio_handle, pin, lgpio.SET_PULL_UP)
                        
                        # Set up edge detection for both rising and falling edges
                        lgpio.gpio_set_debounce_micros(self.lgpio_handle, pin, 10000)  # 10ms debounce
                        
                        # Register callback
                        callback_id = lgpio.callback(self.lgpio_handle, pin, lgpio.BOTH_EDGES, self.gpio_callback)
                        
                        logger.info(f"Set up GPIO pin {pin} for {alarm_key} monitoring")
                        
                    except Exception as e:
                        logger.error(f"Failed to set up GPIO pin {pin}: {e}")
            
            # Main monitoring loop
            while self.is_running:
                self.check_recovery_timers()
                time.sleep(1)  # Check recovery timers every second
                
        except Exception as e:
            logger.error(f"Error in GPIO worker: {e}")
        finally:
            # Cleanup
            if self.lgpio_handle is not None:
                try:
                    lgpio.gpiochip_close(self.lgpio_handle)
                    logger.info("Closed GPIO chip")
                except Exception as e:
                    logger.error(f"Error closing GPIO chip: {e}")
                self.lgpio_handle = None
        
        logger.info("GPIO worker thread stopped")

    def start(self):
        """Start the GPIO module."""
        if not GPIO_AVAILABLE:
            logger.warning("GPIO not available - cannot start GPIO module")
            return False
            
        if self.is_running:
            logger.warning("GPIO module already running")
            return True
            
        # Check if GPIO is enabled in settings
        try:
            from crud.settings import get_setting
            from db import get_db
            db = next(get_db())
            gpio_enabled = get_setting(db, "gpio_enabled", default=False)
            db.close()
            
            if gpio_enabled not in [True, "true", "True", 1, "1"]:
                logger.info("GPIO monitoring disabled in settings")
                return False
        except Exception as e:
            logger.error(f"Error checking GPIO settings: {e}")
            return False
            
        self.is_running = True
        self.gpio_thread = threading.Thread(target=self.gpio_worker, daemon=True)
        self.gpio_thread.start()
        logger.info("GPIO module started")
        return True

    def stop(self):
        """Stop the GPIO module."""
        self.is_running = False
        if self.gpio_thread:
            self.gpio_thread.join(timeout=5.0)
        logger.info("GPIO module stopped")

    def get_status(self) -> dict:
        """Get current status of the GPIO module."""
        return {
            "available": GPIO_AVAILABLE,
            "running": self.is_running,
            "alarm_states": self.alarm_states.copy(),
            "device_settings": self.device_settings.copy(),
            "gpio_map": self.gpio_map.copy()
        }

    def set_alarm_states(self, states: dict):
        """Manually set alarm states (for testing or external control)."""
        old_states = self.alarm_states.copy()
        self.alarm_states.update(states)
        
        if self.alarm_states != old_states:
            logger.info(f"Alarm states manually updated: {self.alarm_states}")
            self.publish_alarm_state()
