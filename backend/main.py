import threading
from serial_reader import serial_loop
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from mqtt_handler import get_mqtt_client
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
from state_manager import (
    set_event_loop, set_mqtt_client, set_serial_mode,
    update_sensor, register_websocket_client, unregister_websocket_client
)
from db import init_db, get_latest_blood_pressure, get_blood_pressure_history, get_last_n_temperature
from mqtt_discovery import send_mqtt_discovery

load_dotenv()

MIN_SPO2=os.getenv("MIN_SPO2")
MAX_SPO2=os.getenv("MAX_SPO2")
MIN_BPM=os.getenv("MIN_BPM")
MAX_BPM=os.getenv("MAX_BPM")
app = FastAPI()

# Store a reference to the MQTT client for shutdown
mqtt_client_ref = None

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
    global mqtt_client_ref
    
    # Initialize database
    init_db()
    
    # 1) Wire in MQTT - only create one client
    mqtt = get_mqtt_client(loop)
    mqtt_client_ref = mqtt  # Store reference for shutdown
    
    try:
        # Connect before setting in state manager
        mqtt.connect(os.getenv("MQTT_BROKER"), int(os.getenv("MQTT_PORT")), 60)
        print(f"[main] Connected to MQTT broker at {os.getenv('MQTT_BROKER')}:{os.getenv('MQTT_PORT')}")
        
        # Send MQTT discovery
        send_mqtt_discovery(mqtt, test_mode=False)
        
        # Set availability to online
        mqtt.publish("medical/spo2/availability", "online", retain=True)
        print(f"[main] Published online status to medical-test/spo2/availability")
        
        # Set the MQTT client in the state manager
        set_mqtt_client(mqtt)
        
        # Start the MQTT loop in a separate thread
        # BUT don't create a new client, use the existing one
        threading.Thread(target=mqtt.loop_forever, daemon=True).start()
    except Exception as e:
        print(f"[main] Failed to connect to MQTT broker: {e}")
    
    # 2) Wire in serial (hot-plug)
    set_event_loop(loop)
    threading.Thread(target=serial_loop, daemon=True).start()

@app.on_event("shutdown")
async def shutdown_event():
    # Use the global reference
    global mqtt_client_ref
    
    if mqtt_client_ref:
        try:
            mqtt_client_ref.publish("medical/spo2/availability", "offline", retain=True)
            print("[main] Published offline status to medical/spo2/availability")
            
            # Properly disconnect
            mqtt_client_ref.disconnect()
        except Exception as e:
            print(f"[main] Failed to publish offline status: {e}")

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

# Add this new route to handle manual vitals
@app.post("/api/vitals/manual")
async def add_manual_vitals(vital_data: dict):
    try:
        # Extract data from the request
        datetime = vital_data.get("datetime")
        bp = vital_data.get("bp", {})
        temp = vital_data.get("temp", {})
        nutrition = vital_data.get("nutrition", {})
        weight = vital_data.get("weight")
        notes = vital_data.get("notes")
        
        # Handle BP data - use existing table
        if bp and (bp.get("systolic_bp") or bp.get("diastolic_bp")):
            systolic = bp.get("systolic_bp")
            diastolic = bp.get("diastolic_bp")
            map_bp = bp.get("map_bp")
            if systolic and diastolic:
                save_blood_pressure(
                    systolic=systolic,
                    diastolic=diastolic,
                    map_value=map_bp or 0,
                    raw_data=json.dumps(bp)
                )
        
        # Handle temperature data - use existing table
        if temp and temp.get("body_temp"):
            body_temp = temp.get("body_temp")
            save_temperature(
                skin_temp=None,  # Only capturing body temp manually
                body_temp=body_temp,
                raw_data=json.dumps(temp)
            )
        
        # Handle other vitals using the new generic vitals table
        if nutrition and nutrition.get("calories"):
            save_vital("calories", nutrition.get("calories"), datetime, notes)
            
        if nutrition and nutrition.get("water_ml"):
            save_vital("water", nutrition.get("water_ml"), datetime, notes)
            
        if weight:
            save_vital("weight", weight, datetime, notes)
        
        # Force state update to include new readings
        broadcast_state()
        
        return {"status": "success", "message": "Vitals saved successfully"}
    except Exception as e:
        print(f"Error saving manual vitals: {str(e)}")
        return {"status": "error", "message": str(e)}

# Add these endpoints after your existing endpoints

@app.get("/api/vitals/{vital_type}")
def get_vital_history(vital_type: str, limit: int = 100):
    """
    Get history for a specific vital type
    
    Args:
        vital_type: Type of vital (weight, calories, water, etc.)
        limit: Maximum number of records to return
    """
    from db import get_vitals_by_type
    return get_vitals_by_type(vital_type, limit)

@app.get("/api/vitals/nutrition")
def get_nutrition_history(limit: int = 100):
    """Get combined nutrition history (calories and water)"""
    from db import get_vitals_by_type
    return {
        "calories": get_vitals_by_type("calories", limit),
        "water": get_vitals_by_type("water", limit)
    }
