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

load_dotenv()

websocket_clients = get_websocket_clients()

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
    # 1) Wire in MQTT
    mqtt = get_mqtt_client(loop)
    set_mqtt_client(mqtt)
    threading.Thread(target=run_mqtt, args=(loop,), daemon=True).start()

    # 2) Wire in serial (hot-plug)
    set_event_loop(loop)
    threading.Thread(target=serial_loop, daemon=True).start()

def run_mqtt(loop):
    mqtt_client = get_mqtt_client(loop)
    mqtt_client.connect(os.getenv("MQTT_BROKER"), int(os.getenv("MQTT_PORT")), 60)
    mqtt_client.loop_forever()

@app.websocket("/ws/sensors")
async def sensor_websocket(websocket: WebSocket):
    await websocket.accept()
    websocket_clients.add(websocket)
    print("WebSocket client connected")

    try:
        while True:
            await websocket.receive_text()  # Keeps connection alive
    except WebSocketDisconnect:
        websocket_clients.discard(websocket)
        print("WebSocket client disconnected")




@app.get("/limits")
def get_limits():
    return {
        "spo2": {"min": MIN_SPO2, "max": MAX_SPO2},
        "bpm": {"min": MIN_BPM, "max": MAX_BPM}
    }
