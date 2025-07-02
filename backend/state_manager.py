# state_manager.py

import asyncio
import json
from sensor_manager import SENSOR_DEFINITIONS
import os
from db import get_last_n_blood_pressure, get_last_n_temperature
from datetime import datetime

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


def broadcast_state():
    """
    Send the full `sensor_state` snapshot over WebSockets to all clients.
    Include the last 5 blood pressure readings and temperature readings.
    """
    if not event_loop:
        print("[state_manager] Cannot broadcast, event_loop not set.")
        return

    # Get the last 5 blood pressure readings
    bp_history = get_last_n_blood_pressure(5)
    
    # Ensure we have valid BP history with default values
    for bp in bp_history:
        if bp['systolic_bp'] is None:
            bp['systolic_bp'] = 0
        if bp['diastolic_bp'] is None:
            bp['diastolic_bp'] = 0
        if bp['map_bp'] is None:
            bp['map_bp'] = 0
        if not bp['datetime']:
            bp['datetime'] = datetime.now().isoformat()
    
    # Get the last 5 temperature readings
    temp_history = get_last_n_temperature(5)
    
    # Ensure we have valid temperature history with default values
    for temp in temp_history:
        if temp['skin_temp'] is None:
            temp['skin_temp'] = 0
        if temp['body_temp'] is None:
            temp['body_temp'] = 0
        if not temp['datetime']:
            temp['datetime'] = datetime.now().isoformat()
    
    # Create a copy of the current state and add histories
    state_copy = sensor_state.copy()
    state_copy['bp'] = bp_history
    state_copy['temp'] = temp_history
    
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
    print(f"[state_manager] Broadcasting state: {message}")
    
    for ws in list(websocket_clients):
        try:
            asyncio.run_coroutine_threadsafe(ws.send_json(message), event_loop)
        except Exception as e:
            print(f"[state_manager] Failed to send to websocket: {e}")
            websocket_clients.discard(ws)


def update_sensor(*args, from_mqtt=False):
    """
    Accepts multiple sensor updates as (name, value) pairs.
    Publishes combined MQTT message and a single WebSocket broadcast.

    Example:
        update_sensor(("spo2", 98), ("bpm", 75), ("perfusion", 3.2))
    """
    updated = {}

    for name, value in args:
        sensor_state[name] = value
        updated[name] = value

    if not updated:
        return  # Nothing to do

    broadcast_state()

    publish_to_mqtt()



# Add this getter
def get_websocket_clients():
    return websocket_clients