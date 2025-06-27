# state_manager.py

import asyncio
import json
from sensor_manager import SENSOR_DEFINITIONS

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

def publish_to_mqtt(name: str, value):
    """
    Publish a single sensor reading to its MQTT topic for Home Assistant.
    - For "bp", `value` is expected to be a list of dicts.
    - For others, it's a single scalar.
    """
    if not mqtt_client:
        return
    topic = SENSOR_DEFINITIONS.get(name)
    if not topic:
        return

    if name == "bp":
        payload = json.dumps(value)
    else:
        payload = json.dumps({name: value})

    mqtt_client.publish(topic, payload, retain=True)


def broadcast_state():
    """
    Send the full `sensor_state` snapshot over WebSockets to all clients.
    """
    if not event_loop:
        return
    message = {
        "type": "sensor_update",
        "state": sensor_state.copy()
    }
    for ws in list(websocket_clients):
        try:
            asyncio.run_coroutine_threadsafe(ws.send_json(message), event_loop)
        except Exception:
            websocket_clients.discard(ws)


def update_sensor(name: str, value):
    """
    Update a sensor value, publish to MQTT, then broadcast to WebSocket clients.
    Call this from both your serial loop and your MQTT on_message.
    """
    sensor_state[name] = value
    publish_to_mqtt(name, value)
    broadcast_state()
