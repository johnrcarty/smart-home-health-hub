import RPi.GPIO2 as GPIO
import threading
import time
from state_manager import update_sensor, broadcast_alert_updates
import logging

# Configure logging
logger = logging.getLogger("app")

# Default GPIO pin groups (device_id -> list of pins)
DEFAULT_GPIO_MAP = {
    "alarm1": [17, 18, 27, 22],
    "alarm2": [5, 6, 13, 19],
}

# Internal flag to avoid spamming updates
device_triggered = {}
device_last_trigger_time = {}
device_recovery_time = {}

# Default recovery time in seconds
DEFAULT_RECOVERY_TIME = 30

def get_device_settings():
    """Get device settings from the database"""
    try:
        from db import get_setting
        
        # Get device mappings from settings
        alarm1_device = get_setting("alarm1_device", "vent")
        alarm2_device = get_setting("alarm2_device", "pulseox")
        
        # Get recovery times from settings (seconds before allowing a new alarm)
        alarm1_recovery = int(get_setting("alarm1_recovery_time", DEFAULT_RECOVERY_TIME))
        alarm2_recovery = int(get_setting("alarm2_recovery_time", DEFAULT_RECOVERY_TIME))
        
        return {
            "alarm1": {
                "device_type": alarm1_device,
                "recovery_time": alarm1_recovery
            },
            "alarm2": {
                "device_type": alarm2_device,
                "recovery_time": alarm2_recovery
            }
        }
    except Exception as e:
        logger.error(f"Error getting device settings: {e}")
        # Return default mappings if settings can't be retrieved
        return {
            "alarm1": {"device_type": "vent", "recovery_time": DEFAULT_RECOVERY_TIME},
            "alarm2": {"device_type": "pulseox", "recovery_time": DEFAULT_RECOVERY_TIME}
        }

def gpio_callback(channel):
    """Callback function for GPIO events"""
    # Get latest settings each time to ensure we have current values
    device_settings = get_device_settings()
    
    for device, pins in DEFAULT_GPIO_MAP.items():
        if channel in pins:
            device_type = device_settings[device]["device_type"]
            recovery_time = device_settings[device]["recovery_time"]
            
            current_time = time.time()
            last_trigger = device_last_trigger_time.get(device, 0)
            
            # Check if we're still in recovery period
            if current_time - last_trigger < device_recovery_time.get(device, 0):
                logger.info(f"Ignoring {device} ({device_type}) trigger on pin {channel} - in recovery period")
                return
                
            logger.info(f"GPIO Triggered: {device} ({device_type}) on pin {channel}")
            
            # Update the trigger time and recovery period
            device_last_trigger_time[device] = current_time
            device_recovery_time[device] = recovery_time
            
            # Mark the device as triggered
            device_triggered[device] = True
            
            # Handle the alarm based on device type
            if device_type == "vent":
                handle_vent_alarm(device, channel)
            elif device_type == "pulseox":
                handle_pulseox_alarm(device, channel)
            else:
                logger.warning(f"Unknown device type: {device_type} for {device}")
                
            # Update external alarm status in state manager
            update_sensor(f"{device_type}_alarm", "TRIGGERED", "external_alarm", True)
            
            # Broadcast alert updates to websocket clients
            broadcast_alert_updates()

def handle_vent_alarm(device, channel):
    """Handle ventilator alarms"""
    try:
        # Update the vent alarm state in the database
        from db import record_ventilator_alarm
        record_ventilator_alarm(device, channel)
        
        # Additional ventilator-specific alarm handling can go here
        logger.info(f"Ventilator alarm recorded for {device} on pin {channel}")
    except Exception as e:
        logger.error(f"Error handling ventilator alarm: {e}")

def handle_pulseox_alarm(device, channel):
    """Handle pulse oximeter alarms"""
    try:
        # Update the pulse ox alarm state in the database
        from db import record_external_pulse_ox_alarm
        record_external_pulse_ox_alarm(device, channel)
        
        # Additional pulse oximeter-specific alarm handling can go here
        logger.info(f"Pulse oximeter alarm recorded for {device} on pin {channel}")
    except Exception as e:
        logger.error(f"Error handling pulse ox alarm: {e}")

def clear_alarm(device_id):
    """Clear an alarm manually or automatically"""
    device_triggered[device_id] = False
    
    # Get device settings
    device_settings = get_device_settings()
    device_type = device_settings.get(device_id, {}).get("device_type", "unknown")
    
    # Update state manager
    update_sensor(f"{device_type}_alarm", "CLEARED", "external_alarm", False)
    
    # Broadcast updates
    broadcast_alert_updates()
    
    logger.info(f"Alarm cleared for {device_id} ({device_type})")

def pin_callback(channel):
    value = GPIO.input(channel)
    logger.info(f">>> GPIO Pin {channel} changed to {'HIGH' if value else 'LOW'}")

def setup_gpio():
    """Set up GPIO pins and event detection"""
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    for device, pins in DEFAULT_GPIO_MAP.items():
        device_triggered[device] = False
        device_last_trigger_time[device] = 0

        for pin in pins:
            try:
                GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
                # Use BOTH edge detection for better debugging
                GPIO.add_event_detect(pin, GPIO.BOTH, callback=pin_callback, bouncetime=100)
                logger.info(f"GPIO pin {pin} set up for {device} with BOTH edge detection")
            except Exception as e:
                logger.error(f"Failed to set up GPIO pin {pin}: {e}")

    logger.info("GPIO monitoring system initialized")

def log_pin_states():
    """Periodically log the current state of all monitored pins."""
    while True:
        states = {pin: GPIO.input(pin) for pins in DEFAULT_GPIO_MAP.values() for pin in pins}
        logger.info(f"Current GPIO pin states: {states}")
        time.sleep(1)

def start_gpio_monitoring():
    """Start GPIO monitoring in a separate thread"""
    try:
        # Start in a separate thread to avoid blocking the main application
        thread = threading.Thread(target=setup_gpio, daemon=True)
        thread.start()
        logger.info("GPIO monitoring thread started")
        return True
    except Exception as e:
        logger.error(f"Failed to start GPIO monitoring: {e}")
        return False

# For testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Starting GPIO test mode")
    start_gpio_monitoring()

    # Start periodic pin state logging in a background thread
    threading.Thread(target=log_pin_states, daemon=True).start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        GPIO.cleanup()
        print("GPIO test mode terminated")