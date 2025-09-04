import lgpio
import threading
import time
from state_manager import set_alarm_states, update_sensor, broadcast_alert_updates, set_alarm_states
import logging

logger = logging.getLogger("app")

DEFAULT_GPIO_MAP = {
    "alarm1": [17, 18, 27, 22],
    "alarm2": [5, 6, 13, 19],
}

device_triggered = {}
device_last_trigger_time = {}
device_recovery_time = {}
DEFAULT_RECOVERY_TIME = 30

# Store the lgpio handle globally
LGPIO_HANDLE = None

alarm_states = {"alarm1": False, "alarm2": False}

def get_device_settings():
    try:
        from crud.settings import get_setting
        from db import get_db
        
        db = next(get_db())
        try:
            alarm1_device = get_setting(db, "alarm1_device", "vent")
            alarm2_device = get_setting(db, "alarm2_device", "pulseox")
            alarm1_recovery = int(get_setting(db, "alarm1_recovery_time", DEFAULT_RECOVERY_TIME))
            alarm2_recovery = int(get_setting(db, "alarm2_recovery_time", DEFAULT_RECOVERY_TIME))
            return {
                "alarm1": {"device_type": alarm1_device, "recovery_time": alarm1_recovery},
                "alarm2": {"device_type": alarm2_device, "recovery_time": alarm2_recovery}
            }
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error getting device settings: {e}")
        return {
            "alarm1": {"device_type": "vent", "recovery_time": DEFAULT_RECOVERY_TIME},
            "alarm2": {"device_type": "pulseox", "recovery_time": DEFAULT_RECOVERY_TIME}
        }

def gpio_callback(gpio, level, tick):
    # This callback is called by lgpio on edge detection
    device_settings = get_device_settings()
    for device, pins in DEFAULT_GPIO_MAP.items():
        if gpio in pins:
            device_type = device_settings[device]["device_type"]
            recovery_time = device_settings[device]["recovery_time"]
            current_time = time.time()
            last_trigger = device_last_trigger_time.get(device, 0)
            if current_time - last_trigger < device_recovery_time.get(device, 0):
                logger.info(f"Ignoring {device} ({device_type}) trigger on pin {gpio} - in recovery period")
                return
            logger.info(f"GPIO Triggered: {device} ({device_type}) on pin {gpio}, level: {level}")
            device_last_trigger_time[device] = current_time
            device_recovery_time[device] = recovery_time
            device_triggered[device] = True
            if device_type == "vent":
                handle_vent_alarm(device, gpio)
            elif device_type == "pulseox":
                handle_pulseox_alarm(device, gpio)
            else:
                logger.warning(f"Unknown device type: {device_type} for {device}")
            update_sensor(f"{device_type}_alarm", "TRIGGERED", "external_alarm", True)
            broadcast_alert_updates()

def handle_vent_alarm(device, gpio):
    try:
        from crud.monitoring import record_ventilator_alarm
        from db import get_db
        
        db = next(get_db())
        try:
            record_ventilator_alarm(db, device, gpio)
            logger.info(f"Ventilator alarm recorded for {device} on pin {gpio}")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error handling ventilator alarm: {e}")

def handle_pulseox_alarm(device, gpio):
    try:
        from crud.monitoring import record_external_pulse_ox_alarm
        from db import get_db
        
        db = next(get_db())
        try:
            record_external_pulse_ox_alarm(db, device, gpio)
            logger.info(f"Pulse oximeter alarm recorded for {device} on pin {gpio}")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error handling pulse ox alarm: {e}")

def clear_alarm(device_id):
    device_triggered[device_id] = False
    device_settings = get_device_settings()
    device_type = device_settings.get(device_id, {}).get("device_type", "unknown")
    update_sensor(f"{device_type}_alarm", "CLEARED", "external_alarm", False)
    broadcast_alert_updates()
    logger.info(f"Alarm cleared for {device_id} ({device_type})")

def setup_gpio():
    global LGPIO_HANDLE
    LGPIO_HANDLE = lgpio.gpiochip_open(0)  # Use gpiochip0
    for device, pins in DEFAULT_GPIO_MAP.items():
        device_triggered[device] = False
        device_last_trigger_time[device] = 0
        for pin in pins:
            try:
                lgpio.gpio_claim_input(LGPIO_HANDLE, pin)
                # Set up BOTH edge detection
                lgpio.gpio_set_debounce(LGPIO_HANDLE, pin, 100)
                lgpio.gpio_register_callback(LGPIO_HANDLE, pin, lgpio.BOTH_EDGES, gpio_callback)
                logger.info(f"GPIO pin {pin} set up for {device} with BOTH edge detection (lgpio)")
            except Exception as e:
                logger.error(f"Failed to set up GPIO pin {pin}: {e}")
    logger.info("GPIO monitoring system initialized (lgpio)")

def log_pin_states():
    global LGPIO_HANDLE
    while True:
        states = {pin: lgpio.gpio_read(LGPIO_HANDLE, pin) for pins in DEFAULT_GPIO_MAP.values() for pin in pins}
        logger.info(f"Current GPIO pin states: {states}")
        time.sleep(1)

def log_alarm_states():
    global LGPIO_HANDLE, alarm_states
    last_alarm_states = {"alarm1": None, "alarm2": None}
    while True:
        for group, pins in DEFAULT_GPIO_MAP.items():
            active = any(lgpio.gpio_read(LGPIO_HANDLE, pin) == 1 for pin in pins)
            if last_alarm_states[group] != active:
                logger.info(f"{group} {'ACTIVE' if active else 'INACTIVE'} (pins: {pins})")
                last_alarm_states[group] = active
                alarm_states[group] = active
                set_alarm_states(alarm_states)  # Update state_manager
        time.sleep(0.5)

def start_gpio_monitoring():
    try:
        thread = threading.Thread(target=setup_gpio, daemon=True)
        thread.start()
        logger.info("GPIO monitoring thread started (lgpio)")
        # Start alarm state logging in a background thread
        threading.Thread(target=log_alarm_states, daemon=True).start()
        return True
    except Exception as e:
        logger.error(f"Failed to start GPIO monitoring: {e}")
        return False

# Add this function to stop GPIO monitoring and set alarm states to false
def stop_gpio_monitoring():
    global LGPIO_HANDLE, alarm_states
    try:
        if LGPIO_HANDLE is not None:
            try:
                lgpio.gpiochip_close(LGPIO_HANDLE)
            except Exception as e:
                logger.error(f"Error closing LGPIO_HANDLE: {e}")
            LGPIO_HANDLE = None
        # Set alarm states to false
        alarm_states["alarm1"] = False
        alarm_states["alarm2"] = False
        set_alarm_states(alarm_states)
        logger.info("GPIO monitoring stopped and alarm states set to false.")
    except Exception as e:
        logger.error(f"Error stopping GPIO monitoring: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Starting GPIO test mode (lgpio)")
    start_gpio_monitoring()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_gpio_monitoring()
        print("GPIO test mode terminated")