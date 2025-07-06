# state_manager.py

import asyncio
import json
from sensor_manager import SENSOR_DEFINITIONS
import os
from db import get_last_n_blood_pressure, get_last_n_temperature
from datetime import datetime
import time

MIN_SPO2 = int(os.getenv("MIN_SPO2", 90))
MAX_SPO2 = int(os.getenv("MAX_SPO2", 100))
MIN_BPM = int(os.getenv("MIN_BPM", 55))
MAX_BPM = int(os.getenv("MAX_BPM", 155))


# -----------------------------------------------------------------------------
# Global state
# -----------------------------------------------------------------------------

# Holds the latest value for each sensor key (e.g. "spo2", "bpm", "bp", etc.)
sensor_state = {name: None for name in SENSOR_DEFINITIONS.keys()}

# Set of active WebSocket connections
websocket_clients = set()

# Flag: are we currently reading from serial (True) or from MQTT (False)?
serial_active = False

# Will be set by your main startup code
mqtt_client = None
event_loop = None

_serial_mode_callbacks = []

from db import get_unacknowledged_alerts_count, save_pulse_ox_data, start_monitoring_alert, update_monitoring_alert

# Add these global variables to track the current alert state
current_alert_id = None
alert_thresholds_exceeded = False
alert_start_data_id = None

# Add these global variables to track recovery timing
alert_recovery_start_time = None
RECOVERY_SECONDS_REQUIRED = 30  # Require 30 seconds of good readings to end an alert


def register_serial_mode_callback(cb):
    """Call `cb(serial_active: bool)` whenever serial_active flips."""
    _serial_mode_callbacks.append(cb)

def set_serial_mode(active: bool):
    global serial_active
    if serial_active == active:
        return
    serial_active = active
    # Notify everyone
    for cb in _serial_mode_callbacks:
        try:
            cb(active)
        except:
            pass

# -----------------------------------------------------------------------------
# Initialization hooks (call at startup)
# -----------------------------------------------------------------------------

def set_event_loop(loop):
    """Provide the asyncio loop for broadcasting WS messages."""
    global event_loop
    event_loop = loop


def set_mqtt_client(client):
    """Provide the paho-mqtt client for publishing to Home Assistant."""
    global mqtt_client
    mqtt_client = client


# -----------------------------------------------------------------------------
# WebSocket client management (used by your FastAPI ws endpoint)
# -----------------------------------------------------------------------------

def register_websocket_client(ws):
    websocket_clients.add(ws)


def unregister_websocket_client(ws):
    websocket_clients.discard(ws)


# -----------------------------------------------------------------------------
# Serial-mode control
# -----------------------------------------------------------------------------

def set_serial_mode(active: bool):
    """Flip between serial (True) and MQTT (False) input modes."""
    global serial_active
    serial_active = active


def is_serial_mode() -> bool:
    return serial_active


# -----------------------------------------------------------------------------
# Core update / broadcast logic
# -----------------------------------------------------------------------------

def publish_to_mqtt():
    """
    Publish current sensor state to Home Assistant MQTT topics
    following the format of the original script.
    """
    if not mqtt_client:
        print("[state_manager] Cannot publish to MQTT, mqtt_client not set.")
        return
    
    # Check if MQTT client is connected
    try:
        if not mqtt_client.is_connected():
            print("[state_manager] MQTT client is not connected. Attempting to reconnect...")
            mqtt_client.reconnect()
    except Exception as e:
        print(f"[state_manager] Error checking MQTT connection: {e}")
        return
    
    # Use medical-test prefix for testing
    base_topic = "medical/spo2/state"
    
    # Status to motion conversion
    if sensor_state["status"] is None:
        motion = "OFF"
    else:
        motion = "ON" if "MO" in sensor_state["status"] else "OFF"

    # Alarm Logic
    if sensor_state["spo2"] is None:
        spo2_alarm = "OFF"
    else:
        spo2_alarm = "ON" if not (MIN_SPO2 <= int(sensor_state["spo2"]) <= MAX_SPO2) else "OFF"

    if sensor_state["bpm"] is None:
        hr_alarm = "OFF"
    else:
        hr_alarm = "ON" if not (MIN_BPM <= int(sensor_state["bpm"]) <= MAX_BPM) else "OFF"

    # Create payload matching the original script format
    timestamp = datetime.now().strftime("%y-%b-%d %H:%M:%S")
    
    payload = {
        "timestamp": timestamp,
        "spo2": sensor_state["spo2"],
        "bpm": sensor_state["bpm"],
        "pa": sensor_state["perfusion"],
        "status": sensor_state["status"],
        "motion": motion,
        "spo2_alarm": spo2_alarm,
        "hr_alarm": hr_alarm
    }

    # Send to test topic with better error handling
    try:
        json_payload = json.dumps(payload)
        result = mqtt_client.publish(base_topic, json_payload, retain=True)
        
        # Check the result
        if result.rc == 0:
            print(f"[state_manager] Published to {base_topic}: {json_payload}")
        else:
            print(f"[state_manager] Failed to publish to {base_topic}, result code: {result.rc}")
            
        # Also publish availability
        mqtt_client.publish("medical-test/spo2/availability", "online", retain=True)
    except Exception as e:
        print(f"[state_manager] Error publishing to MQTT: {e}")


def check_thresholds(spo2=None, bpm=None):
    """Check if values are within threshold limits"""
    
    # Get threshold values from settings or environment variables
    from db import get_setting
    min_spo2 = get_setting("min_spo2", MIN_SPO2)
    max_spo2 = get_setting("max_spo2", MAX_SPO2)
    min_bpm = get_setting("min_bpm", MIN_BPM)
    max_bpm = get_setting("max_bpm", MAX_BPM)
    
    spo2_alarm = False
    hr_alarm = False
    
    if spo2 is not None:
        spo2_alarm = not (min_spo2 <= spo2 <= max_spo2)
        
    if bpm is not None:
        hr_alarm = not (min_bpm <= bpm <= max_bpm)
        
    return spo2_alarm, hr_alarm


def broadcast_state():
    """
    Send the full `sensor_state` snapshot over WebSockets to all clients.
    Include alert counts, BP readings, temperature readings, and settings.
    """
    if not event_loop:
        print("[state_manager] Cannot broadcast, event_loop not set.")
        return

    # Get the last 5 blood pressure readings
    bp_history = get_last_n_blood_pressure(5)
    
    # Get the last 5 temperature readings
    temp_history = get_last_n_temperature(5)
    
    # Get all settings
    from db import get_all_settings
    settings = get_all_settings()
    
    # Get unacknowledged alerts count
    alerts_count = get_unacknowledged_alerts_count()
    
    # Create a copy of the current state and add histories
    state_copy = sensor_state.copy()
    state_copy['bp'] = bp_history
    state_copy['temp'] = temp_history
    state_copy['settings'] = settings
    state_copy['alerts_count'] = alerts_count
    
    # Ensure all values have defaults
    for key in state_copy:
        if key != 'bp' and key != 'temp' and state_copy[key] is None:
            # Use a sentinel value that your frontend can recognize
            state_copy[key] = -1
    
    print(f"[state_manager] Broadcasting to {len(websocket_clients)} clients.")
    message = {
        "type": "sensor_update",
        "state": state_copy
    }
    
    for ws in list(websocket_clients):
        try:
            asyncio.run_coroutine_threadsafe(ws.send_json(message), event_loop)
        except Exception as e:
            print(f"[state_manager] Failed to send to websocket: {e}")
            websocket_clients.discard(ws)


# Replace the duplicate update_sensor function with a single, combined version

# Remove this first update_sensor function (around line 241)
# def update_sensor(*args, from_mqtt=False):
#     """
#     Accepts multiple sensor updates as (name, value) pairs.
#     Publishes combined MQTT message and a single WebSocket broadcast.
#
#     Example:
#         update_sensor(("spo2", 98), ("bpm", 75), ("perfusion", 3.2))
#     """
#     updated = {}
#
#     for name, value in args:
#         sensor_state[name] = value
#         updated[name] = value
#
#     if not updated:
#         return  # Nothing to do
#
#     broadcast_state()
#
#     publish_to_mqtt()


# Modify this second update_sensor function to include the MQTT publishing (around line 286)
def update_sensor(*updates, from_mqtt=False):
    """
    Update sensor state values, track alerts, and broadcast changes
    
    Args:
        *updates: pairs of (sensor_name, value) to update
        from_mqtt: Whether this update is from MQTT (vs serial)
    """
    global current_alert_id, alert_thresholds_exceeded, alert_start_data_id, sensor_state
    global alert_recovery_start_time
    
    has_pulse_ox_updates = False
    pulse_ox_data = {
        'spo2': None,
        'bpm': None,
        'perfusion': None,
        'status': None
    }
    
    updated = {}  # Track what's been updated for MQTT publishing
    
    # First, update all the values
    for i in range(0, len(updates), 2):
        if i+1 < len(updates):  # Make sure we have a pair
            sensor_name = updates[i]
            value = updates[i+1]
            
            # Update global state
            sensor_state[sensor_name] = value
            updated[sensor_name] = value
            
            # Track pulse ox related updates
            if sensor_name in pulse_ox_data:
                pulse_ox_data[sensor_name] = value
                has_pulse_ox_updates = True
    
    # If no updates, exit early
    if not updated:
        return
        
    # If we received pulse ox data, check for alerts
    if has_pulse_ox_updates and (pulse_ox_data['spo2'] is not None or pulse_ox_data['bpm'] is not None):
        spo2_alarm, hr_alarm = check_thresholds(pulse_ox_data['spo2'], pulse_ox_data['bpm'])
        
        # Save data to the continuous log
        data_id = save_pulse_ox_data(
            spo2=pulse_ox_data['spo2'], 
            bpm=pulse_ox_data['bpm'],
            pa=pulse_ox_data['perfusion'],
            status=pulse_ox_data['status'],
            motion="ON" if sensor_state.get("motion", False) else "OFF",
            spo2_alarm="ON" if spo2_alarm else "OFF",
            hr_alarm="ON" if hr_alarm else "OFF",
            raw_data=json.dumps(pulse_ox_data)
        )
        
        # Check if we need to start or update an alert
        is_alert_condition = spo2_alarm or hr_alarm
        
        if is_alert_condition and not alert_thresholds_exceeded:
            # We've just crossed the threshold, start a new alert
            alert_thresholds_exceeded = True
            alert_recovery_start_time = None  # Reset recovery timer
            alert_start_data_id = data_id
            current_alert_id = start_monitoring_alert(
                spo2=pulse_ox_data['spo2'],
                bpm=pulse_ox_data['bpm'],
                data_id=data_id,
                spo2_alarm_triggered=1 if spo2_alarm else 0,
                hr_alarm_triggered=1 if hr_alarm else 0
            )
            
        elif is_alert_condition and alert_thresholds_exceeded and current_alert_id:
            # Continuing alert, update min/max values
            alert_recovery_start_time = None  # Reset recovery timer if we're in alert condition
            update_monitoring_alert(
                alert_id=current_alert_id,
                spo2=pulse_ox_data['spo2'],
                bpm=pulse_ox_data['bpm'],
                spo2_alarm_triggered=1 if spo2_alarm else None,
                hr_alarm_triggered=1 if hr_alarm else None
            )
            
        elif not is_alert_condition and alert_thresholds_exceeded and current_alert_id:
            # Values are now within normal range, but we're still in an alert state
            # Start or continue tracking recovery time
            current_time = time.time()
            
            if alert_recovery_start_time is None:
                # First good reading after an alert, start recovery timer
                alert_recovery_start_time = current_time
                print(f"[state_manager] Alert recovery started at {datetime.fromtimestamp(alert_recovery_start_time).isoformat()}")
                
                # Still update the min/max values during recovery period
                update_monitoring_alert(
                    alert_id=current_alert_id,
                    spo2=pulse_ox_data['spo2'],
                    bpm=pulse_ox_data['bpm']
                )
            elif (current_time - alert_recovery_start_time) >= RECOVERY_SECONDS_REQUIRED:
                # We've had good readings for the required duration, finalize the alert
                now = datetime.now().isoformat()
                print(f"[state_manager] Alert recovery completed after {RECOVERY_SECONDS_REQUIRED} seconds at {now}")
                
                update_monitoring_alert(
                    alert_id=current_alert_id,
                    end_time=now,
                    end_data_id=data_id,
                    spo2=pulse_ox_data['spo2'],
                    bpm=pulse_ox_data['bpm']
                )
                alert_thresholds_exceeded = False
                current_alert_id = None
                alert_recovery_start_time = None
            else:
                # Still in recovery period, update the alert but don't end it yet
                elapsed = current_time - alert_recovery_start_time
                remaining = RECOVERY_SECONDS_REQUIRED - elapsed
                print(f"[state_manager] Alert recovery in progress: {elapsed:.1f}s elapsed, {remaining:.1f}s remaining")
                
                # Update min/max values during recovery period
                update_monitoring_alert(
                    alert_id=current_alert_id,
                    spo2=pulse_ox_data['spo2'],
                    bpm=pulse_ox_data['bpm']
                )
    
    # Broadcast updated state
    broadcast_state()
    
    # Publish to MQTT if needed
    publish_to_mqtt()