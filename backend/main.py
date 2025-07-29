import threading
from serial_reader import serial_loop
import asyncio
import json  # Add this import
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from mqtt_handler import get_mqtt_client
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
from state_manager import (
    set_event_loop, set_mqtt_client, set_serial_mode,
    update_sensor, register_websocket_client, unregister_websocket_client,
    broadcast_state
)
from crud import (get_latest_blood_pressure, get_blood_pressure_history, get_last_n_temperature, save_blood_pressure,
                  save_temperature, save_vital, get_vitals_by_type, get_all_settings, get_setting, save_setting,
                  delete_setting,
                  add_equipment, get_equipment_list, log_equipment_change, get_equipment_change_history,
                  get_distinct_vital_types,
                  get_vitals_by_type_paginated)
from mqtt_discovery import send_mqtt_discovery
# Reset sensor state to clear any bad data
from state_manager import reset_sensor_state
import logging
from fastapi.responses import JSONResponse
from gpio_monitor import start_gpio_monitoring, stop_gpio_monitoring, set_alarm_states
from db import get_db

load_dotenv()

MIN_SPO2 = os.getenv("MIN_SPO2")
MAX_SPO2 = os.getenv("MAX_SPO2")
MIN_BPM = os.getenv("MIN_BPM")
MAX_BPM = os.getenv("MAX_BPM")
app = FastAPI()

# Initialize a logger for your application
logger = logging.getLogger("app")

# Configure logging
logging.basicConfig(level=logging.INFO)

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

    # Set the event loop
    set_event_loop(asyncio.get_event_loop())
    print("[main] Event loop registered with state manager")

    # Initialize default settings if they don't exist
    db = next(get_db())
    reset_sensor_state()

    # Device settings
    if await get_setting(db, "device_name") is None:
        save_setting(db, "device_name", "Smart Home Health Monitor", "string", "Device name")

    if await get_setting(db, "device_location") is None:
        save_setting(db, "device_location", "Bedroom", "string", "Device location")

    # Alert thresholds - use environment variables as defaults if available
    if await get_setting(db, "min_spo2") is None:
        save_setting(db, "min_spo2", os.getenv("MIN_SPO2", 90), "int", "Minimum SpO2 threshold")

    if await get_setting(db, "max_spo2") is None:
        save_setting(db, "max_spo2", os.getenv("MAX_SPO2", 100), "int", "Maximum SpO2 threshold")

    if await get_setting(db, "min_bpm") is None:
        save_setting(db, "min_bpm", os.getenv("MIN_BPM", 55), "int", "Minimum heart rate threshold")

    if await get_setting(db, "max_bpm") is None:
        save_setting(db, "max_bpm", os.getenv("MAX_BPM", 155), "int", "Maximum heart rate threshold")

    # Display settings
    if await get_setting(db, "temp_unit") is None:
        save_setting(db, "temp_unit", "F", "string", "Temperature unit (F or C)")

    if await get_setting(db, "weight_unit") is None:
        save_setting(db, "weight_unit", "lbs", "string", "Weight unit (lbs or kg)")

    if await get_setting(db, "dark_mode") is None:
        save_setting(db, "dark_mode", True, "bool", "Dark mode enabled")

    # Initialize default GPIO alarm settings if they don't exist
    if await get_setting(db, "alarm1_device") is None:
        save_setting(db, "alarm1_device", "vent", "string", "Device type for Alarm 1 RJ9 port")

    if await get_setting(db, "alarm2_device") is None:
        save_setting(db, "alarm2_device", "pulseox", "string", "Device type for Alarm 2 RJ9 port")

    if await get_setting(db, "alarm1_recovery_time") is None:
        save_setting(db, "alarm1_recovery_time", 30, "int", "Recovery time in seconds for Alarm 1")

    if await get_setting(db, "alarm2_recovery_time") is None:
        save_setting(db, "alarm2_recovery_time", 30, "int", "Recovery time in seconds for Alarm 2")

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

    # Start GPIO monitoring only if enabled
    gpio_enabled = await get_setting(db, "gpio_enabled", default=False)
    if gpio_enabled in [True, "true", "True", 1, "1"]:
        start_gpio_monitoring()
    else:
        # Set alarm states to false if not enabled
        set_alarm_states({"alarm1": False, "alarm2": False})


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
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print(f"[main] WebSocket client connected: {websocket}")
    register_websocket_client(websocket)

    try:
        while True:
            # Just keep the connection alive
            data = await websocket.receive_text()
            # You can handle commands here if needed
    except WebSocketDisconnect:
        print(f"[main] WebSocket client disconnected: {websocket}")
        unregister_websocket_client(websocket)
    except Exception as e:
        print(f"[main] WebSocket error: {e}")
        unregister_websocket_client(websocket)


@app.get("/limits")
def get_limits():
    return {
        "spo2": {"min": MIN_SPO2, "max": MAX_SPO2},
        "bpm": {"min": MIN_BPM, "max": MAX_BPM}
    }


# Add new endpoints to access blood pressure data
@app.get("/blood-pressure/latest")
def latest_blood_pressure():
    db = next(get_db())
    return get_latest_blood_pressure(db) or {"message": "No data available"}


@app.get("/blood-pressure/history")
def blood_pressure_history(limit: int = 100):
    db = next(get_db())
    return get_blood_pressure_history(db, limit)


# Add new endpoints to access temperature data
@app.get("/temperature/latest")
def latest_temperature():
    db = next(get_db())
    temps = get_last_n_temperature(db, 1)
    return temps[0] if temps else {"message": "No data available"}


@app.get("/temperature/history")
def temperature_history(limit: int = 100):
    db = next(get_db())
    return get_last_n_temperature(db, limit)


# Add this new route to handle manual vitals
@app.post("/api/vitals/manual")
async def add_manual_vitals(vital_data: dict):
    db = next(get_db())
    try:
        datetime_val = vital_data.get("datetime")
        notes = vital_data.get("notes")
        # Handle blood pressure
        bp = vital_data.get("bp", {})
        if bp and (bp.get("systolic_bp") or bp.get("diastolic_bp")):
            systolic = bp.get("systolic_bp")
            diastolic = bp.get("diastolic_bp")
            map_bp = bp.get("map_bp")
            if systolic and diastolic:
                save_blood_pressure(
                    db,
                    systolic=systolic,
                    diastolic=diastolic,
                    map_value=map_bp or 0,
                    raw_data=json.dumps(bp)
                )
        # Handle temperature
        temp = vital_data.get("temp", {})
        if temp and temp.get("body_temp"):
            body_temp = temp.get("body_temp")
            save_temperature(
                db,
                skin_temp=None,
                body_temp=body_temp,
                raw_data=json.dumps(temp)
            )
        # Handle bathroom
        bathroom_type = vital_data.get("bathroom_type")
        bathroom_size = vital_data.get("bathroom_size")
        bathroom_size_map = ["smear", "s", "m", "l", "xl"]
        if bathroom_type and bathroom_size:
            try:
                value = bathroom_size_map.index(bathroom_size)
            except ValueError:
                value = None
            save_vital(db, "bathroom", value, datetime_val, notes, vital_group=bathroom_type)
        # Dynamically handle all other vitals
        for key, value in vital_data.items():
            if key in ["datetime", "bp", "temp", "notes", "bathroom_type", "bathroom_size"]:
                continue
            if value is None or value == "":
                continue
            save_vital(db, key, value, datetime_val, notes)
        broadcast_state()
        return {"status": "success", "message": "Vitals saved successfully"}
    except Exception as e:
        print(f"Error saving manual vitals: {str(e)}")
        return {"status": "error", "message": str(e)}


# Add these endpoints after your existing endpoints

@app.get("/api/vitals/{vital_type}")
def get_vital_history(vital_type: str, limit: int = 100):
    db = next(get_db())
    return get_vitals_by_type(db, vital_type, limit)


@app.get("/api/vitals/nutrition")
def get_nutrition_history(limit: int = 100):
    """Get combined nutrition history (calories and water)"""
    from crud import get_vitals_by_type
    return {
        "calories": get_vitals_by_type("calories", limit),
        "water": get_vitals_by_type("water", limit)
    }


@app.get("/api/vitals/types")
def get_vital_types():
    """
    Get a distinct list of vital_type values from the vitals table
    """
    db = next(get_db())
    return get_distinct_vital_types(db)


@app.get("/api/vitals/history")
def get_vital_history_paginated(vital_type: str, page: int = 1, page_size: int = 20):
    """
    Get paginated history for a specific vital type
    """
    return get_vitals_by_type_paginated(vital_type, page, page_size)


# Add these imports
from fastapi import Body, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List


# Add these models for request validation
class SettingIn(BaseModel):
    value: Any
    data_type: str = "string"
    description: Optional[str] = None


class SettingUpdate(BaseModel):
    settings: Dict[str, Any]


# Add these endpoints
@app.get("/api/settings")
async def get_all_settings():
    """Get all settings"""
    from crud import get_all_settings
    db = next(get_db())
    return get_all_settings(db)


@app.get("/api/settings/{key}")
async def get_setting(key: str, default: Optional[str] = None):
    """Get a specific setting by key"""
    from crud import get_setting
    db = next(get_db())
    value = get_setting(key, default)
    if value is None and default is None:
        raise HTTPException(status_code=404, detail=f"Setting {key} not found")
    return {"key": key, "value": value}


@app.post("/api/settings/{key}")
async def set_setting(key: str, setting: SettingIn):
    """Set a specific setting"""
    from crud import save_setting
    db = next(get_db())
    success = save_setting(
        db,
        key=key,
        value=setting.value,
        data_type=setting.data_type,
        description=setting.description
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save setting")
    broadcast_state()
    return {"key": key, "value": setting.value, "status": "success"}


@app.post("/api/settings")
async def update_multiple_settings(settings: SettingUpdate):
    """Update multiple settings at once"""
    from crud import save_setting
    db = next(get_db())
    results = {}
    gpio_enabled_changed = False
    gpio_enabled_new = None
    for key, value in settings.settings.items():
        if key == "gpio_enabled":
            gpio_enabled_new = value if not isinstance(value, dict) else value.get("value")
            gpio_enabled_changed = True
        if isinstance(value, dict) and "value" in value:
            data_type = value.get("data_type", "string")
            description = value.get("description")
            actual_value = value["value"]
            success = save_setting(db, key, actual_value, data_type, description)
        else:
            success = save_setting(db, key, value)
        results[key] = "success" if success else "failed"
    broadcast_state()
    if gpio_enabled_changed:
        if gpio_enabled_new in [True, "true", "True", 1, "1"]:
            start_gpio_monitoring()
        else:
            stop_gpio_monitoring()
            set_alarm_states({"alarm1": False, "alarm2": False})
    return results


@app.delete("/api/settings/{key}")
async def delete_setting_endpoint(key: str):
    """Delete a setting"""
    from crud import delete_setting
    db = next(get_db())
    success = delete_setting(db, key)
    if not success:
        raise HTTPException(status_code=404, detail=f"Setting {key} not found")
    broadcast_state()
    return {"status": "success", "message": f"Setting {key} deleted"}


# Add these endpoints

@app.get("/api/monitoring/alerts")
async def get_monitoring_alerts_endpoint(
        limit: int = 50,
        include_acknowledged: bool = False,
        detailed: bool = False
):
    """Get monitoring alerts"""
    from crud import get_monitoring_alerts
    return get_monitoring_alerts(limit, include_acknowledged, detailed)


@app.get("/api/monitoring/alerts/count")
async def get_unacknowledged_alerts_count_endpoint():
    """Get count of unacknowledged alerts"""
    from crud import get_unacknowledged_alerts_count
    return {"count": get_unacknowledged_alerts_count()}


@app.post("/api/monitoring/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: int, data: dict = Body(...)):
    """
    Acknowledge an alert and save oxygen usage data
    """
    try:
        # Now logger is defined
        logger.info(f"Acknowledging alert {alert_id} with data: {data}")

        # Extract oxygen data from the request
        oxygen_used = data.get('oxygen_used', 0)
        oxygen_highest = data.get('oxygen_highest')
        oxygen_unit = data.get('oxygen_unit')

        logger.info(f"Processed data: used={oxygen_used}, highest={oxygen_highest}, unit={oxygen_unit}")

        # Make sure we handle null values properly
        if oxygen_highest == "":
            oxygen_highest = None

        # Update the alert with oxygen information
        from crud import update_monitoring_alert, acknowledge_alert
        success = update_monitoring_alert(
            alert_id,
            oxygen_used=oxygen_used,
            oxygen_highest=oxygen_highest,
            oxygen_unit=oxygen_unit
        )

        # Then acknowledge the alert
        if success:
            result = acknowledge_alert(alert_id)

            if result:
                return {"success": True, "message": "Alert acknowledged"}
            else:
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=404,
                    content={"detail": f"Alert {alert_id} not found"}
                )
        else:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=500,
                content={"detail": f"Failed to update alert {alert_id}"}
            )
    except Exception as e:
        # Now logger is defined
        logger.error(f"Error acknowledging alert: {e}", exc_info=True)
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error acknowledging alert: {str(e)}"}
        )


@app.get("/api/monitoring/data")
async def get_pulse_ox_data_endpoint(
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 1000
):
    """Get pulse ox data within a time range"""
    # This would require implementing a new function in db.py
    # We'll just return a placeholder for now
    return {"message": "Feature coming soon"}


# Add this endpoint to fetch alert data

@app.get("/api/monitoring/alerts/{alert_id}/data")
async def get_alert_data(alert_id: int):
    """Get detailed data for a specific alert event"""
    from crud import get_pulse_ox_data_for_alert

    try:
        data = get_pulse_ox_data_for_alert(alert_id)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving alert data: {str(e)}")


from crud import add_equipment, get_equipment_list, log_equipment_change, get_equipment_change_history


@app.post("/api/equipment")
async def api_add_equipment(data: dict = Body(...)):
    """Add new equipment item."""
    name = data.get('name')
    last_changed = data.get('last_changed')
    useful_days = data.get('useful_days')
    if not name or not last_changed or not useful_days:
        return JSONResponse(status_code=400, content={"detail": "Missing required fields"})
    eid = add_equipment(name, last_changed, useful_days)
    return {"id": eid, "status": "success"}


@app.get("/api/equipment")
async def api_get_equipment():
    """Get equipment list sorted by due next."""
    db = next(get_db())
    return get_equipment_list(db)


@app.post("/api/equipment/{equipment_id}/change")
async def api_log_equipment_change(equipment_id: int, data: dict = Body(...)):
    """Log a change and update last_changed."""
    changed_at = data.get('changed_at')
    if not changed_at:
        return JSONResponse(status_code=400, content={"detail": "Missing changed_at"})
    success = log_equipment_change(equipment_id, changed_at)
    return {"success": success}


@app.get("/api/equipment/{equipment_id}/history")
async def api_get_equipment_history(equipment_id: int):
    """Get change history for equipment."""
    return get_equipment_change_history(equipment_id)
