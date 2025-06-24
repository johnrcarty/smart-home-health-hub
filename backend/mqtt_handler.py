import os
import paho.mqtt.client as mqtt
from sensor_manager import SENSOR_DEFINITIONS
from dotenv import load_dotenv
import asyncio

load_dotenv()

# MQTT Config
MQTT_BROKER = os.getenv("MQTT_BROKER")
MQTT_PORT = int(os.getenv("MQTT_PORT"))
MQTT_CLIENT_ID = os.getenv("MQTT_CLIENT_ID", "sensor_monitor")
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")

# Track latest sensor values, initialized as None
sensor_state = {name: None for name in SENSOR_DEFINITIONS.keys()}

# WebSocket connections
websocket_clients = set()

def get_websocket_clients():
    return websocket_clients

def get_mqtt_client(loop):
    client = mqtt.Client(client_id=MQTT_CLIENT_ID)

    if MQTT_USERNAME and MQTT_PASSWORD:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print(f"Connected to MQTT Broker at {MQTT_BROKER}:{MQTT_PORT}")
            for topic in SENSOR_DEFINITIONS.values():
                client.subscribe(topic)
                print(f"Subscribed to {topic}")
        else:
            print(f"Failed to connect to MQTT Broker, code {rc}")

    def on_message(client, userdata, msg):
        print(f"MQTT Message received on {msg.topic}: {msg.payload.decode()}")

        # Find which sensor this topic belongs to
        matching_sensor = next(
            (name for name, topic in SENSOR_DEFINITIONS.items() if topic == msg.topic), None
        )

        if matching_sensor:
            sensor_state[matching_sensor] = msg.payload.decode()

            # Build full state payload
            data = {
                "type": "sensor_update",
                "state": sensor_state.copy()
            }

            # Broadcast to all WebSocket clients
            for websocket in list(websocket_clients):
                try:
                    asyncio.run_coroutine_threadsafe(websocket.send_json(data), loop)
                except Exception as e:
                    print(f"WebSocket send failed: {e}")
                    websocket_clients.discard(websocket)
        else:
            print(f"Received message for unknown topic: {msg.topic}")

    client.on_connect = on_connect
    client.on_message = on_message

    return client
