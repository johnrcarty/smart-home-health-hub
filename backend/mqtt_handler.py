import json
import os
import paho.mqtt.client as mqtt
from sensor_manager import SENSOR_DEFINITIONS
from state_manager import get_websocket_clients, update_sensor, broadcast_state
from db import save_blood_pressure, save_temperature  # Add save_temperature import

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

    # Update the on_message function to save raw data

    def on_message(client, userdata, msg):
        raw_data = msg.payload.decode()
        print(f"MQTT Message received on {msg.topic}: {raw_data}")
        matching_sensor = next(
            (name for name, topic in SENSOR_DEFINITIONS.items() if topic == msg.topic), None
        )

        if matching_sensor:
            try:
                payload = json.loads(raw_data)
                
                # Handle blood pressure data specifically
                if msg.topic == "shh/map/state":
                    # Extract values from the payload
                    systolic = payload.get("systolic")
                    diastolic = payload.get("diastolic")
                    map_value = payload.get("map")
                    
                    # Save to database if we have all valid values (not None and not all zeros)
                    if (systolic is not None and diastolic is not None and map_value is not None and
                        not (systolic == 0 and diastolic == 0 and map_value == 0)):
                        save_blood_pressure(
                            systolic=systolic,
                            diastolic=diastolic,
                            map_value=map_value,
                            raw_data=raw_data
                        )
                        # Force a state broadcast to include the new BP reading
                        broadcast_state()
                    else:
                        print(f"Ignoring invalid BP values: systolic={systolic}, diastolic={diastolic}, map={map_value}")
                
                # Handle temperature data specifically
                elif msg.topic == "shh/temp/state":
                    # Extract values from the payload
                    skin_temp = payload.get("skin_temp")
                    body_temp = payload.get("body_temp")
                    
                    # Save to database if we have valid values (not None and not both zeros)
                    if (skin_temp is not None and body_temp is not None and
                        not (skin_temp == 0 and body_temp == 0)):
                        save_temperature(
                            skin_temp=skin_temp,
                            body_temp=body_temp,
                            raw_data=raw_data
                        )
                        # Update sensor values in state manager
                        update_sensor(("skin_temp", skin_temp), from_mqtt=True)
                        update_sensor(("body_temp", body_temp), from_mqtt=True)
                        # Force a state broadcast to include the new temperature reading
                        broadcast_state()
                    else:
                        print(f"Ignoring invalid temperature values: skin_temp={skin_temp}, body_temp={body_temp}")
                
                # Handle spo2 data specifically 
                elif msg.topic == "shh/spo2/state" or msg.topic == "shh/bpm/state" or msg.topic == "shh/perfusion/state":
                    # Add sensor update with raw data
                    update_sensor(matching_sensor, payload.get(matching_sensor), "raw_data", raw_data)
                    return
                
                # Continue with normal processing for other sensors
                else:
                    value = payload.get(matching_sensor)
                    if value is not None:
                        update_sensor((matching_sensor, value), from_mqtt=True)
                    else:
                        print(f"Warning: {matching_sensor} not found in payload {payload}")
                    
            except json.JSONDecodeError:
                print(f"Failed to decode JSON: {msg.payload}")
            except Exception as e:
                print(f"Error processing message on {msg.topic}: {e}")
        else:
            print(f"Received message for unknown topic: {msg.topic}")

    client.on_connect = on_connect
    client.on_message = on_message

    return client
