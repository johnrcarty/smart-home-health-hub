import threading
from serial_reader import serial_loop
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from mqtt_handler import get_mqtt_client, get_websocket_clients
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
from state_manager import (
    set_event_loop, set_mqtt_client, set_serial_mode,
    update_sensor, register_websocket_client
)
from state_manager import register_websocket_client, unregister_websocket_client
from db import init_db, get_latest_blood_pressure, get_blood_pressure_history, get_last_n_temperature
from mqtt_discovery import send_mqtt_discovery

load_dotenv()

MIN_SPO2=os.getenv("MIN_SPO2")
MAX_SPO2=os.getenv("MAX_SPO2")
MIN_BPM=os.getenv("MIN_BPM")
MAX_BPM=os.getenv("MAX_BPM")
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

loop = asyncio.get_event_loop()

@app.on_event("startup")
async def startup_event():
    # Initialize database
    init_db()
    
    # 1) Wire in MQTT
    mqtt = get_mqtt_client(loop)
    
    try:
        mqtt.connect(os.getenv("MQTT_BROKER"), int(os.getenv("MQTT_PORT")), 60)
        print(f"[main] Connected to MQTT broker at {os.getenv('MQTT_BROKER')}:{os.getenv('MQTT_PORT')}")
        
        # Send MQTT discovery
        send_mqtt_discovery(mqtt, test_mode=True)
        
        # Set availability to online
        mqtt.publish("medical-test/spo2/availability", "online", retain=True)
        print(f"[main] Published online status to medical-test/spo2/availability")
    except Exception as e:
        print(f"[main] Failed to connect to MQTT broker: {e}")
    
    set_mqtt_client(mqtt)
    threading.Thread(target=run_mqtt, args=(loop,), daemon=True).start()

    # 2) Wire in serial (hot-plug)
    set_event_loop(loop)
    threading.Thread(target=serial_loop, daemon=True).start()

@app.on_event("shutdown")
async def shutdown_event():
    if mqtt_client:
        try:
            mqtt_client.publish("medical-test/spo2/availability", "offline", retain=True)
            print("[main] Published offline status to medical-test/spo2/availability")
        except Exception as e:
            print(f"[main] Failed to publish offline status: {e}")

def run_mqtt(loop):
    mqtt_client = get_mqtt_client(loop)
    mqtt_client.connect(os.getenv("MQTT_BROKER"), int(os.getenv("MQTT_PORT")), 60)
    mqtt_client.loop_forever()

@app.websocket("/ws/sensors")
async def sensor_websocket(websocket: WebSocket):
    await websocket.accept()
    register_websocket_client(websocket)
    print("WebSocket client connected")

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        unregister_websocket_client(websocket)
        print("WebSocket client disconnected")

@app.get("/limits")
def get_limits():
    return {
        "spo2": {"min": MIN_SPO2, "max": MAX_SPO2},
        "bpm": {"min": MIN_BPM, "max": MAX_BPM}
    }

# Add new endpoints to access blood pressure data
@app.get("/blood-pressure/latest")
def latest_blood_pressure():
    return get_latest_blood_pressure() or {"message": "No data available"}

@app.get("/blood-pressure/history")
def blood_pressure_history(limit: int = 100):
    return get_blood_pressure_history(limit)

# Add new endpoints to access temperature data
@app.get("/temperature/latest")
def latest_temperature():
    temps = get_last_n_temperature(1)
    return temps[0] if temps else {"message": "No data available"}

@app.get("/temperature/history")
def temperature_history(limit: int = 100):
    return get_last_n_temperature(limit)
