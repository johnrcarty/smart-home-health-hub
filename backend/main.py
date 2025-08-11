import threading
from serial_reader import serial_loop
import asyncio
import json  # Add this import
import platform
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from models import Equipment
from mqtt_handler import get_mqtt_client
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
from state_manager import (
    set_event_loop, set_mqtt_client, set_serial_mode,
    update_sensor, register_websocket_client, unregister_websocket_client,
    broadcast_state, get_serial_log, is_serial_mode
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
from db import get_db
from crud import add_medication, get_active_medications, get_inactive_medications, update_medication, delete_medication, add_medication_schedule, get_medication_schedules, get_all_medication_schedules, update_medication_schedule, delete_medication_schedule, toggle_medication_schedule_active, get_daily_medication_schedule, add_care_task, get_active_care_tasks, get_inactive_care_tasks, update_care_task, delete_care_task, add_care_task_schedule, get_care_task_schedules, get_all_care_task_schedules, update_care_task_schedule, delete_care_task_schedule, toggle_care_task_schedule_active, get_daily_care_task_schedule, add_care_task_category, get_care_task_categories, update_care_task_category, delete_care_task_category

load_dotenv()

# Platform detection for GPIO functionality
def is_raspberry_pi():
    """Check if running on Raspberry Pi"""
    try:
        with open('/proc/cpuinfo', 'r') as f:
            return any('BCM' in line for line in f)
    except (FileNotFoundError, PermissionError):
        return False

def is_gpio_available():
    """Check if GPIO functionality is available"""
    if not is_raspberry_pi():
        return False
    try:
        import lgpio
        return True
    except ImportError:
        return False

# Determine GPIO availability
GPIO_AVAILABLE = is_gpio_available()
if GPIO_AVAILABLE:
    print("[main] GPIO functionality available - running on Raspberry Pi")
else:
    print("[main] GPIO functionality not available - running on non-Raspberry Pi system")

# GPIO fallback functions for non-Raspberry Pi systems
def fallback_set_alarm_states(states):
    """Fallback function when GPIO is not available"""
    print(f"[main] GPIO fallback: Would set alarm states to {states}")

def fallback_start_gpio_monitoring():
    """Fallback function when GPIO is not available"""
    print("[main] GPIO fallback: Would start GPIO monitoring")
    return True

def fallback_stop_gpio_monitoring():
    """Fallback function when GPIO is not available"""
    print("[main] GPIO fallback: Would stop GPIO monitoring")

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
    if get_setting(db, "device_name") is None:
        save_setting(db, "device_name", "Smart Home Health Monitor", "string", "Device name")

    if get_setting(db, "device_location") is None:
        save_setting(db, "device_location", "Bedroom", "string", "Device location")

    # Alert thresholds - use environment variables as defaults if available
    if get_setting(db, "min_spo2") is None:
        save_setting(db, "min_spo2", os.getenv("MIN_SPO2", 90), "int", "Minimum SpO2 threshold")

    if get_setting(db, "max_spo2") is None:
        save_setting(db, "max_spo2", os.getenv("MAX_SPO2", 100), "int", "Maximum SpO2 threshold")

    if get_setting(db, "min_bpm") is None:
        save_setting(db, "min_bpm", os.getenv("MIN_BPM", 55), "int", "Minimum heart rate threshold")

    if get_setting(db, "max_bpm") is None:
        save_setting(db, "max_bpm", os.getenv("MAX_BPM", 155), "int", "Maximum heart rate threshold")

    # Display settings
    if get_setting(db, "temp_unit") is None:
        save_setting(db, "temp_unit", "F", "string", "Temperature unit (F or C)")

    if get_setting(db, "weight_unit") is None:
        save_setting(db, "weight_unit", "lbs", "string", "Weight unit (lbs or kg)")

    if get_setting(db, "dark_mode") is None:
        save_setting(db, "dark_mode", True, "bool", "Dark mode enabled")

    # Initialize default GPIO alarm settings if they don't exist
    if get_setting(db, "alarm1_device") is None:
        save_setting(db, "alarm1_device", "vent", "string", "Device type for Alarm 1 RJ9 port")

    if get_setting(db, "alarm2_device") is None:
        save_setting(db, "alarm2_device", "pulseox", "string", "Device type for Alarm 2 RJ9 port")

    if get_setting(db, "alarm1_recovery_time") is None:
        save_setting(db, "alarm1_recovery_time", 30, "int", "Recovery time in seconds for Alarm 1")

    if get_setting(db, "alarm2_recovery_time") is None:
        save_setting(db, "alarm2_recovery_time", 30, "int", "Recovery time in seconds for Alarm 2")

    # 1) Wire in MQTT - only create one client if enabled
    mqtt = get_mqtt_client(loop)
    mqtt_client_ref = mqtt  # Store reference for shutdown

    if mqtt:  # Only proceed if MQTT is enabled and configured
        try:
            # Get MQTT settings from database
            from mqtt_handler import get_mqtt_settings
            mqtt_settings = get_mqtt_settings()
            
            # Connect using database settings
            mqtt.connect(mqtt_settings['broker'], mqtt_settings['port'], 60)
            logger.info(f"[main] Connected to MQTT broker at {mqtt_settings['broker']}:{mqtt_settings['port']}")

            # Send MQTT discovery if enabled
            discovery_enabled = get_setting(db, 'mqtt_discovery_enabled', True)
            test_mode = get_setting(db, 'mqtt_test_mode', True)
            
            if discovery_enabled:
                send_mqtt_discovery(mqtt, test_mode=test_mode)

            # Set availability to online using base topic from settings
            base_topic = get_setting(db, 'mqtt_base_topic', 'shh')
            mqtt.publish(f"{base_topic}/spo2/availability", "online", retain=True)
            logger.info(f"[main] Published online status to {base_topic}/spo2/availability")

            # Set the MQTT client in the state manager
            set_mqtt_client(mqtt)

            # Start the MQTT loop in a separate thread
            threading.Thread(target=mqtt.loop_forever, daemon=True).start()
        except Exception as e:
            logger.error(f"[main] Failed to connect to MQTT broker: {e}")
    else:
        logger.info("[main] MQTT is disabled or not configured")

    # 2) Wire in serial (hot-plug)
    set_event_loop(loop)
    threading.Thread(target=serial_loop, daemon=True).start()

    # Start GPIO monitoring only if enabled and available
    gpio_enabled = get_setting(db, "gpio_enabled", default=False)
    if gpio_enabled in [True, "true", "True", 1, "1"]:
        if GPIO_AVAILABLE:
            try:
                from gpio_monitor import start_gpio_monitoring
                start_gpio_monitoring()
                print("[main] GPIO monitoring started")
            except Exception as e:
                print(f"[main] Failed to start GPIO monitoring: {e}")
                fallback_start_gpio_monitoring()
        else:
            print("[main] GPIO monitoring requested but not available on this platform")
            fallback_start_gpio_monitoring()
    else:
        # Set alarm states to false if not enabled
        if GPIO_AVAILABLE:
            try:
                from gpio_monitor import set_alarm_states
                set_alarm_states({"alarm1": False, "alarm2": False})
                print("[main] GPIO disabled - alarm states set to false")
            except Exception as e:
                print(f"[main] Failed to set alarm states: {e}")
                fallback_set_alarm_states({"alarm1": False, "alarm2": False})
        else:
            fallback_set_alarm_states({"alarm1": False, "alarm2": False})


@app.on_event("shutdown")
async def shutdown_event():
    # Use the global reference
    global mqtt_client_ref

    if mqtt_client_ref:
        try:
            # Get base topic from settings for proper offline message
            db = next(get_db())
            base_topic = get_setting(db, 'mqtt_base_topic', 'shh')
            db.close()
            
            mqtt_client_ref.publish(f"{base_topic}/spo2/availability", "offline", retain=True)
            logger.info(f"[main] Published offline status to {base_topic}/spo2/availability")

            # Properly disconnect
            mqtt_client_ref.disconnect()
        except Exception as e:
            logger.error(f"[main] Failed to publish offline status: {e}")
    else:
        logger.info("[main] No MQTT client to disconnect")


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
def latest_blood_pressure(db: Session = Depends(get_db)):
    return get_latest_blood_pressure(db) or {"message": "No data available"}


@app.get("/blood-pressure/history")
def blood_pressure_history(limit: int = 100, db: Session = Depends(get_db)):
    return get_blood_pressure_history(db, limit)


# Add new endpoints to access temperature data
@app.get("/temperature/latest")
def latest_temperature(db: Session = Depends(get_db)):
    temps = get_last_n_temperature(db, 1)
    return temps[0] if temps else {"message": "No data available"}


@app.get("/temperature/history")
def temperature_history(limit: int = 100, db: Session = Depends(get_db)):
    return get_last_n_temperature(db, limit)


# Add this new route to handle manual vitals
@app.post("/api/vitals/manual")
async def add_manual_vitals(vital_data: dict, db: Session = Depends(get_db)):
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

@app.get("/api/vitals/types")
def get_vital_types(db: Session = Depends(get_db)):
    """
    Get a distinct list of vital_type values from the vitals table
    """
    return get_distinct_vital_types(db)


@app.get("/api/vitals/nutrition")
def get_nutrition_history(limit: int = 100):
    """Get combined nutrition history (calories and water)"""
    from crud import get_vitals_by_type
    return {
        "calories": get_vitals_by_type("calories", limit),
        "water": get_vitals_by_type("water", limit)
    }


@app.get("/api/vitals/history")
def get_vital_history_paginated(vital_type: str, page: int = 1, page_size: int = 20, db: Session = Depends(get_db)):
    """
    Get paginated history for a specific vital type
    """
    return get_vitals_by_type_paginated(db, vital_type, page, page_size)


@app.get("/api/vitals/{vital_type}")
def get_vital_history(vital_type: str, limit: int = 100, db: Session = Depends(get_db)):
    return get_vitals_by_type(db, vital_type, limit)


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
async def get_all_settings(db: Session = Depends(get_db)):
    """Get all settings"""
    from crud import get_all_settings
    return get_all_settings(db)


@app.get("/api/settings/{key}")
async def get_setting_api(key: str, default: Optional[str] = None, db: Session = Depends(get_db)):
    """Get a specific setting by key"""
    from crud import get_setting
    value = get_setting(db, key, default)
    if value is None and default is None:
        raise HTTPException(status_code=404, detail=f"Setting {key} not found")
    return {"key": key, "value": value}


@app.post("/api/settings/{key}")
async def set_setting(key: str, setting: SettingIn, db: Session = Depends(get_db)):
    """Set a specific setting"""
    from crud import save_setting
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
async def update_multiple_settings(settings: SettingUpdate, db: Session = Depends(get_db)):
    """Update multiple settings at once"""
    from crud import save_setting
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
            if GPIO_AVAILABLE:
                try:
                    from gpio_monitor import start_gpio_monitoring
                    start_gpio_monitoring()
                    print("[main] GPIO monitoring enabled via settings")
                except Exception as e:
                    print(f"[main] Failed to start GPIO monitoring: {e}")
                    fallback_start_gpio_monitoring()
            else:
                print("[main] GPIO monitoring requested but not available on this platform")
                fallback_start_gpio_monitoring()
        else:
            if GPIO_AVAILABLE:
                try:
                    from gpio_monitor import stop_gpio_monitoring, set_alarm_states
                    stop_gpio_monitoring()
                    set_alarm_states({"alarm1": False, "alarm2": False})
                    print("[main] GPIO monitoring disabled via settings")
                except Exception as e:
                    print(f"[main] Failed to stop GPIO monitoring: {e}")
                    fallback_stop_gpio_monitoring()
                    fallback_set_alarm_states({"alarm1": False, "alarm2": False})
            else:
                fallback_stop_gpio_monitoring()
                fallback_set_alarm_states({"alarm1": False, "alarm2": False})
    return results


@app.delete("/api/settings/{key}")
async def delete_setting_endpoint(key: str, db: Session = Depends(get_db)):
    """Delete a setting"""
    from crud import delete_setting
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
    db = next(get_db())
    try:
        return get_monitoring_alerts(db, limit, include_acknowledged, detailed)
    finally:
        db.close()


@app.get("/api/monitoring/alerts/count")
async def get_unacknowledged_alerts_count_endpoint():
    """Get count of unacknowledged alerts"""
    from crud import get_unacknowledged_alerts_count
    db = next(get_db())
    try:
        return {"count": get_unacknowledged_alerts_count(db)}
    finally:
        db.close()


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
async def api_add_equipment(data: dict = Body(...), db: Session = Depends(get_db)):
    """Add new equipment item."""
    name = data.get('name')
    quantity = data.get('quantity', 1)
    scheduled_replacement = data.get('scheduled_replacement', True)
    last_changed = data.get('last_changed')
    useful_days = data.get('useful_days')
    
    if not name:
        return JSONResponse(status_code=400, content={"detail": "Name is required"})
    
    if scheduled_replacement and (not last_changed or not useful_days):
        return JSONResponse(status_code=400, content={"detail": "Last changed and useful days are required for scheduled replacements"})
    
    eid = add_equipment(db, name, quantity, scheduled_replacement, last_changed, useful_days)
    return {"id": eid, "status": "success"}


@app.get("/api/equipment")
async def api_get_equipment(db: Session = Depends(get_db)):
    """Get equipment list sorted by due next."""
    return get_equipment_list(db)


@app.post("/api/equipment/{equipment_id}/change")
async def api_log_equipment_change(equipment_id: int, data: dict = Body(...), db: Session = Depends(get_db)):
    """Log a change and update last_changed."""
    changed_at = data.get('changed_at')
    if not changed_at:
        return JSONResponse(status_code=400, content={"detail": "Missing changed_at"})
    
    # Check if equipment has scheduled replacement
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        return JSONResponse(status_code=404, content={"detail": "Equipment not found"})
    
    if not equipment.scheduled_replacement:
        return JSONResponse(status_code=400, content={"detail": "Equipment does not have scheduled replacement"})
    
    success = log_equipment_change(db, equipment_id, changed_at)
    return {"success": success}


@app.get("/api/equipment/{equipment_id}/history")
async def api_get_equipment_history(equipment_id: int, db: Session = Depends(get_db)):
    """Get change history for equipment."""
    return get_equipment_change_history(db, equipment_id)


@app.post("/api/add/medication")
async def api_add_medication(data: dict = Body(...), db: Session = Depends(get_db)):
    """Add a new medication entry."""
    required_fields = ["name", "concentration", "quantity", "quantity_unit", "instructions", "start_date", "as_needed", "notes"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return JSONResponse(status_code=400, content={"detail": f"Missing fields: {', '.join(missing)}"})

    # Extract fields
    name = data["name"]
    concentration = data["concentration"]
    quantity = data["quantity"]
    quantity_unit = data["quantity_unit"]
    instructions = data["instructions"]
    start_date = data["start_date"]
    as_needed = data["as_needed"]
    notes = data["notes"]
    end_date = data.get("end_date")  # Optional, not required in add form

    try:
        med_id = add_medication(
            db,
            name=name,
            concentration=concentration,
            quantity=quantity,
            quantity_unit=quantity_unit,
            instructions=instructions,
            start_date=start_date,
            end_date=end_date,
            as_needed=as_needed,
            notes=notes
        )
        return {"id": med_id, "status": "success"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})


@app.get("/api/medications/active")
async def get_active_medications_endpoint(db: Session = Depends(get_db)):
    """Get all active medications."""
    from crud import get_active_medications
    return get_active_medications(db)

@app.get("/api/medications/inactive")
async def get_inactive_medications_endpoint(db: Session = Depends(get_db)):
    """Get all inactive medications."""
    from crud import get_inactive_medications
    return get_inactive_medications(db)

@app.put("/api/medications/{med_id}")
async def update_medication_endpoint(med_id: int, data: dict = Body(...), db: Session = Depends(get_db)):
    """Update an existing medication."""
    from crud import update_medication
    
    # Remove id from data if present
    data.pop('id', None)
    
    success = update_medication(db, med_id, **data)
    if not success:
        return JSONResponse(status_code=404, content={"detail": "Medication not found"})
    
    return {"status": "success"}

@app.delete("/api/medications/{med_id}")
async def delete_medication_endpoint(med_id: int, db: Session = Depends(get_db)):
    """Delete (soft delete) a medication."""
    from crud import delete_medication
    
    success = delete_medication(db, med_id)
    if not success:
        return JSONResponse(status_code=404, content={"detail": "Medication not found"})
    
    return {"status": "success"}

@app.post("/api/medications/{med_id}/toggle-active")
async def toggle_medication_active_endpoint(med_id: int, db: Session = Depends(get_db)):
    """Toggle the active status of a medication."""
    from crud import update_medication
    from models import Medication
    
    # Get current medication
    medication = db.query(Medication).filter(Medication.id == med_id).first()
    if not medication:
        return JSONResponse(status_code=404, content={"detail": "Medication not found"})
    
    # Toggle active status
    success = update_medication(db, med_id, active=not medication.active)
    if not success:
        return JSONResponse(status_code=500, content={"detail": "Failed to update medication"})
    
    return {"status": "success", "active": not medication.active}

# Medication Schedule Endpoints

@app.post("/api/add/schedule/{medication_id}")
async def api_add_medication_schedule(
    medication_id: int, 
    data: dict = Body(...), 
    db: Session = Depends(get_db)
):
    """Add a new medication schedule entry."""
    try:
        schedule_type = data.get('type', 'med')
        if schedule_type != 'med':
            return JSONResponse(
                status_code=400, 
                content={"detail": f"Schedule type '{schedule_type}' not supported. Only 'med' is currently supported."}
            )
        
        # Validate required fields
        required_fields = ['cron_expression', 'description', 'dose_amount']
        for field in required_fields:
            if field not in data:
                return JSONResponse(
                    status_code=400, 
                    content={"detail": f"Missing required field: {field}"}
                )
        
        # Verify medication exists
        from models import Medication
        medication = db.query(Medication).filter(Medication.id == medication_id).first()
        if not medication:
            return JSONResponse(status_code=404, content={"detail": "Medication not found"})
        
        schedule_id = add_medication_schedule(
            db,
            medication_id=medication_id,
            cron_expression=data['cron_expression'],
            description=data['description'],
            dose_amount=data['dose_amount'],
            active=data.get('active', True),
            notes=data.get('notes', '')
        )
        
        if schedule_id:
            return {"status": "success", "schedule_id": schedule_id}
        else:
            return JSONResponse(status_code=500, content={"detail": "Failed to add medication schedule"})
    
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"Internal server error: {str(e)}"})

@app.get("/api/medications/{medication_id}/schedules")
async def get_medication_schedules_endpoint(medication_id: int, db: Session = Depends(get_db)):
    """Get all schedules for a specific medication."""
    # Verify medication exists
    from models import Medication
    medication = db.query(Medication).filter(Medication.id == medication_id).first()
    if not medication:
        return JSONResponse(status_code=404, content={"detail": "Medication not found"})
    
    schedules = get_medication_schedules(db, medication_id)
    return {"schedules": schedules}

@app.get("/api/schedules")
async def get_all_medication_schedules_endpoint(active_only: bool = True, db: Session = Depends(get_db)):
    """Get all medication schedules, optionally filtering by active status."""
    schedules = get_all_medication_schedules(db, active_only)
    return {"schedules": schedules}

@app.put("/api/schedules/{schedule_id}")
async def update_medication_schedule_endpoint(
    schedule_id: int, 
    data: dict = Body(...), 
    db: Session = Depends(get_db)
):
    """Update an existing medication schedule."""
    # Remove id from data if present
    data.pop('id', None)
    
    success = update_medication_schedule(db, schedule_id, **data)
    if not success:
        return JSONResponse(status_code=404, content={"detail": "Medication schedule not found"})
    
    return {"status": "success"}

@app.delete("/api/schedules/{schedule_id}")
async def delete_medication_schedule_endpoint(schedule_id: int, db: Session = Depends(get_db)):
    """Delete a medication schedule."""
    success = delete_medication_schedule(db, schedule_id)
    if not success:
        return JSONResponse(status_code=404, content={"detail": "Medication schedule not found"})
    
    return {"status": "success"}

@app.post("/api/schedules/{schedule_id}/toggle-active")
async def toggle_medication_schedule_active_endpoint(schedule_id: int, db: Session = Depends(get_db)):
    """Toggle the active status of a medication schedule."""
    success, new_active_status = toggle_medication_schedule_active(db, schedule_id)
    if not success:
        return JSONResponse(status_code=404, content={"detail": "Medication schedule not found"})
    
    return {"status": "success", "active": new_active_status}

@app.get("/api/schedules/daily")
async def get_daily_medication_schedule_endpoint(db: Session = Depends(get_db)):
    """Get today's scheduled medications plus yesterday's missed medications."""
    try:
        daily_schedule = get_daily_medication_schedule(db)
        return daily_schedule
    except Exception as e:
        logger.error(f"Error getting daily medication schedule: {e}")
        return JSONResponse(
            status_code=500, 
            content={"detail": f"Error retrieving daily schedule: {str(e)}"}
        )

# Add a test endpoint to verify server is working
@app.get("/api/test")
async def test_endpoint():
    return {"status": "success", "message": "API is working"}

# Dev endpoint to trigger websocket broadcast
@app.post("/api/dev/broadcast")
async def trigger_broadcast():
    """Trigger a websocket broadcast for development/testing purposes"""
    try:
        broadcast_state()
        return {"status": "success", "message": "Websocket broadcast triggered"}
    except Exception as e:
        logger.error(f"Error triggering broadcast: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error triggering broadcast: {str(e)}"}
        )


@app.post("/api/equipment/{equipment_id}/receive")
async def api_receive_equipment(equipment_id: int, data: dict = Body(...), db: Session = Depends(get_db)):
    """Increase equipment quantity (receive new stock)."""
    amount = data.get('amount', 1)
    from crud import receive_equipment
    success = receive_equipment(db, equipment_id, amount)
    return {"success": success}

@app.post("/api/equipment/{equipment_id}/open")
async def api_open_equipment(equipment_id: int, data: dict = Body(...), db: Session = Depends(get_db)):
    """Decrease equipment quantity (open/use equipment)."""
    amount = data.get('amount', 1)
    from crud import open_equipment
    success = open_equipment(db, equipment_id, amount)
    return {"success": success}


@app.post("/api/medications/{med_id}/administer")
async def administer_medication(med_id: int, data: dict = Body(...), db: Session = Depends(get_db)):
    """Record a medication administration and deduct from quantity."""
    from crud import administer_medication
    dose_amount = data.get('dose_amount')
    schedule_id = data.get('schedule_id')
    scheduled_time = data.get('scheduled_time')
    notes = data.get('notes')
    result = administer_medication(db, med_id, dose_amount, schedule_id, scheduled_time, notes)
    if not result:
        return JSONResponse(status_code=400, content={"detail": "Failed to administer medication"})
    return {"success": True}

@app.get("/api/medications/history")
async def get_medication_history_endpoint(
    limit: int = 25,
    medication_name: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get medication administration history with filtering options
    
    Query parameters:
    - limit: Maximum number of records (default 25)
    - medication_name: Filter by medication name (partial match)
    - start_date: Filter by start date (YYYY-MM-DD format)
    - end_date: Filter by end date (YYYY-MM-DD format)
    - status_filter: Filter by status ('late', 'early', 'missed', 'on-time')
    """
    from crud import get_medication_history
    
    try:
        history = get_medication_history(
            db=db,
            limit=limit,
            medication_name=medication_name,
            start_date=start_date,
            end_date=end_date,
            status_filter=status_filter
        )
        return {"history": history, "count": len(history)}
    except Exception as e:
        logger.error(f"Error getting medication history: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error retrieving medication history: {str(e)}"}
        )

@app.get("/api/medications/names")
async def get_medication_names_endpoint(db: Session = Depends(get_db)):
    """
    Get all medication names for dropdown selection
    Returns active medications first, then inactive ones with indicators
    """
    from crud import get_medication_names_for_dropdown
    
    try:
        medication_names = get_medication_names_for_dropdown(db)
        return {"medication_names": medication_names}
    except Exception as e:
        logger.error(f"Error getting medication names: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error retrieving medication names: {str(e)}"}
        )


# Care Task Endpoints

@app.post("/api/add/care-task")
async def api_add_care_task(data: dict = Body(...), db: Session = Depends(get_db)):
    """Add a new care task"""
    try:
        task_id = add_care_task(
            db=db,
            name=data.get("name"),
            description=data.get("description"),
            category_id=data.get("category_id"),
            active=data.get("active", True)
        )
        if task_id:
            return {"message": "Care task added successfully", "id": task_id}
        else:
            return JSONResponse(
                status_code=500,
                content={"detail": "Failed to add care task"}
            )
    except Exception as e:
        logger.error(f"Error adding care task: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error adding care task: {str(e)}"}
        )

@app.get("/api/care-tasks/active")
async def get_active_care_tasks_endpoint(db: Session = Depends(get_db)):
    """Get all active care tasks with their schedules"""
    try:
        care_tasks = get_active_care_tasks(db)
        return {"care_tasks": care_tasks}
    except Exception as e:
        logger.error(f"Error getting active care tasks: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error retrieving active care tasks: {str(e)}"}
        )

@app.get("/api/care-tasks/inactive")
async def get_inactive_care_tasks_endpoint(db: Session = Depends(get_db)):
    """Get all inactive care tasks with their schedules"""
    try:
        care_tasks = get_inactive_care_tasks(db)
        return {"care_tasks": care_tasks}
    except Exception as e:
        logger.error(f"Error getting inactive care tasks: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error retrieving inactive care tasks: {str(e)}"}
        )

@app.put("/api/care-tasks/{task_id}")
async def update_care_task_endpoint(task_id: int, data: dict = Body(...), db: Session = Depends(get_db)):
    """Update an existing care task"""
    try:
        success = update_care_task(db, task_id, **data)
        if success:
            return {"message": "Care task updated successfully"}
        else:
            return JSONResponse(
                status_code=404,
                content={"detail": "Care task not found"}
            )
    except Exception as e:
        logger.error(f"Error updating care task {task_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error updating care task: {str(e)}"}
        )

@app.delete("/api/care-tasks/{task_id}")
async def delete_care_task_endpoint(task_id: int, db: Session = Depends(get_db)):
    """Delete (deactivate) a care task"""
    try:
        success = delete_care_task(db, task_id)
        if success:
            return {"message": "Care task deleted successfully"}
        else:
            return JSONResponse(
                status_code=404,
                content={"detail": "Care task not found"}
            )
    except Exception as e:
        logger.error(f"Error deleting care task {task_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error deleting care task: {str(e)}"}
        )

@app.post("/api/care-tasks/{task_id}/toggle-active")
async def toggle_care_task_active_endpoint(task_id: int, db: Session = Depends(get_db)):
    """Toggle active status of a care task"""
    try:
        # Get current task
        care_tasks = get_active_care_tasks(db) + get_inactive_care_tasks(db)
        task = next((t for t in care_tasks if t['id'] == task_id), None)
        
        if not task:
            return JSONResponse(
                status_code=404,
                content={"detail": "Care task not found"}
            )
        
        # Toggle active status
        new_active_status = not task['active']
        success = update_care_task(db, task_id, active=new_active_status)
        
        if success:
            return {"message": f"Care task {'activated' if new_active_status else 'deactivated'} successfully"}
        else:
            return JSONResponse(
                status_code=500,
                content={"detail": "Failed to toggle care task status"}
            )
    except Exception as e:
        logger.error(f"Error toggling care task {task_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error toggling care task status: {str(e)}"}
        )

# Care Task Schedule Endpoints

@app.post("/api/add/care-task-schedule/{care_task_id}")
async def api_add_care_task_schedule(
    care_task_id: int, 
    data: dict = Body(...), 
    db: Session = Depends(get_db)
):
    """Add a schedule to a care task"""
    try:
        schedule_id = add_care_task_schedule(
            db=db,
            care_task_id=care_task_id,
            cron_expression=data.get("cron_expression"),
            description=data.get("description"),
            active=data.get("active", True),
            notes=data.get("notes")
        )
        if schedule_id:
            return {"message": "Care task schedule added successfully", "schedule_id": schedule_id}
        else:
            return JSONResponse(
                status_code=500,
                content={"detail": "Failed to add care task schedule"}
            )
    except Exception as e:
        logger.error(f"Error adding care task schedule: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error adding care task schedule: {str(e)}"}
        )

@app.get("/api/care-tasks/{care_task_id}/schedules")
async def get_care_task_schedules_endpoint(care_task_id: int, db: Session = Depends(get_db)):
    """Get all schedules for a specific care task"""
    try:
        schedules = get_care_task_schedules(db, care_task_id)
        return {"schedules": schedules}
    except Exception as e:
        logger.error(f"Error getting care task schedules: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error retrieving care task schedules: {str(e)}"}
        )

@app.get("/api/care-task-schedules")
async def get_all_care_task_schedules_endpoint(active_only: bool = True, db: Session = Depends(get_db)):
    """Get all care task schedules"""
    try:
        schedules = get_all_care_task_schedules(db, active_only)
        return {"schedules": schedules}
    except Exception as e:
        logger.error(f"Error getting all care task schedules: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error retrieving care task schedules: {str(e)}"}
        )

@app.get("/api/care-task-schedules/daily")
async def get_daily_care_task_schedule_endpoint(db: Session = Depends(get_db)):
    """Get today's care task schedule"""
    try:
        schedule = get_daily_care_task_schedule(db)
        return schedule
    except Exception as e:
        logger.error(f"Error getting daily care task schedule: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error retrieving daily care task schedule: {str(e)}"}
        )

@app.post("/api/care-tasks/{task_id}/complete")
async def complete_care_task_endpoint(task_id: int, data: dict = Body(...), db: Session = Depends(get_db)):
    """Complete a care task"""
    try:
        from crud import complete_care_task
        log_id = complete_care_task(
            db=db,
            task_id=task_id,
            schedule_id=data.get("schedule_id"),
            scheduled_time=data.get("scheduled_time"),
            notes=data.get("notes"),
            status=data.get("status", "completed")
        )
        if log_id:
            return {"message": "Care task completed successfully", "log_id": log_id}
        else:
            return JSONResponse(
                status_code=500,
                content={"detail": "Failed to complete care task"}
            )
    except Exception as e:
        logger.error(f"Error completing care task {task_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error completing care task: {str(e)}"}
        )


# Care Task Category Endpoints

@app.post("/api/add/care-task-category")
async def api_add_care_task_category(data: dict = Body(...), db: Session = Depends(get_db)):
    """Add a new care task category"""
    try:
        category_id = add_care_task_category(
            db=db,
            name=data.get("name"),
            description=data.get("description"),
            color=data.get("color"),
            is_default=data.get("is_default", False),
            active=data.get("active", True)
        )
        if category_id:
            return {"message": "Care task category added successfully", "id": category_id}
        else:
            return JSONResponse(
                status_code=500,
                content={"detail": "Failed to add care task category"}
            )
    except Exception as e:
        logger.error(f"Error adding care task category: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error adding care task category: {str(e)}"}
        )

@app.get("/api/care-task-categories")
async def get_care_task_categories_endpoint(active_only: bool = True, db: Session = Depends(get_db)):
    """Get all care task categories"""
    try:
        categories = get_care_task_categories(db, active_only)
        return {"categories": categories}
    except Exception as e:
        logger.error(f"Error getting care task categories: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error retrieving care task categories: {str(e)}"}
        )

@app.put("/api/care-task-categories/{category_id}")
async def update_care_task_category_endpoint(category_id: int, data: dict = Body(...), db: Session = Depends(get_db)):
    """Update an existing care task category"""
    try:
        success = update_care_task_category(db, category_id, **data)
        if success:
            return {"message": "Care task category updated successfully"}
        else:
            return JSONResponse(
                status_code=404,
                content={"detail": "Care task category not found"}
            )
    except Exception as e:
        logger.error(f"Error updating care task category {category_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error updating care task category: {str(e)}"}
        )

@app.delete("/api/care-task-categories/{category_id}")
async def delete_care_task_category_endpoint(category_id: int, db: Session = Depends(get_db)):
    """Delete a care task category (only if not default and no tasks assigned)"""
    try:
        success = delete_care_task_category(db, category_id)
        if success:
            return {"message": "Care task category deleted successfully"}
        else:
            return JSONResponse(
                status_code=400,
                content={"detail": "Cannot delete category: either it's a default category or has tasks assigned"}
            )
    except Exception as e:
        logger.error(f"Error deleting care task category {category_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error deleting care task category: {str(e)}"}
        )


# MQTT Settings Endpoints
@app.get("/api/mqtt/settings")
async def get_mqtt_settings(db: Session = Depends(get_db)):
    """Get current MQTT settings"""
    try:
        settings = {}
        mqtt_keys = [
            'mqtt_enabled', 'mqtt_broker', 'mqtt_port', 'mqtt_username', 
            'mqtt_password', 'mqtt_client_id', 'mqtt_discovery_enabled', 
            'mqtt_test_mode', 'mqtt_base_topic'
        ]
        
        for key in mqtt_keys:
            setting = get_setting(db, key)
            if setting is not None:
                settings[key] = setting
            else:
                # Default values
                defaults = {
                    'mqtt_enabled': False,
                    'mqtt_broker': '',
                    'mqtt_port': 1883,
                    'mqtt_username': '',
                    'mqtt_password': '',
                    'mqtt_client_id': 'sensor_monitor',
                    'mqtt_discovery_enabled': True,
                    'mqtt_test_mode': True,
                    'mqtt_base_topic': 'shh'
                }
                settings[key] = defaults.get(key, '')
        
        # Load topic configurations
        topics_setting = get_setting(db, 'mqtt_topics')
        default_topics = get_default_mqtt_topics()
        merged_topics = default_topics.copy()
        if topics_setting is not None:
            # topics_setting is already parsed by get_setting when data_type is 'json'
            if isinstance(topics_setting, dict):
                for k, v in topics_setting.items():
                    merged_topics[k] = v
            else:
                try:
                    loaded_topics = json.loads(str(topics_setting))
                    for k, v in loaded_topics.items():
                        merged_topics[k] = v
                except json.JSONDecodeError:
                    pass  # fallback to defaults
        settings['topics'] = merged_topics
        
        return settings
    except Exception as e:
        logger.error(f"Error getting MQTT settings: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error retrieving MQTT settings: {str(e)}"}
        )

def get_default_mqtt_topics():
    """Get default MQTT topic configuration"""
    return {
        'spo2': {
            'enabled': True,
            'broadcast_topic': 'shh/spo2/state',
            'listen_topic': 'shh/spo2/set'
        },
        'bpm': {
            'enabled': True,
            'broadcast_topic': 'shh/bpm/state',
            'listen_topic': 'shh/bpm/set'
        },
        'perfusion': {
            'enabled': True,
            'broadcast_topic': 'shh/perfusion/state',
            'listen_topic': 'shh/perfusion/set'
        },
        'blood_pressure': {
            'enabled': True,
            'broadcast_topic': 'shh/bp/state',
            'listen_topic': 'shh/bp/set'
        },
        'temperature': {
            'enabled': True,
            'broadcast_topic': 'shh/temp/state',
            'listen_topic': 'shh/temp/set'
        },
        'nutrition': {
            'enabled': False,
            'water_broadcast_topic': 'shh/water/state',
            'water_listen_topic': 'shh/water/set',
            'calories_broadcast_topic': 'shh/calories/state',
            'calories_listen_topic': 'shh/calories/set'
        },
        'weight': {
            'enabled': False,
            'broadcast_topic': 'shh/weight/state',
            'listen_topic': 'shh/weight/set'
        },
        'bathroom': {
            'enabled': False,
            'broadcast_topic': 'shh/bathroom/state',
            'listen_topic': 'shh/bathroom/set'
        },
        'spo2_alarm': {
            'enabled': True,
            'broadcast_topic': 'shh/alarms/spo2',
            'listen_topic': 'shh/alarms/spo2/set'
        },
        'bpm_alarm': {
            'enabled': True,
            'broadcast_topic': 'shh/alarms/bpm',
            'listen_topic': 'shh/alarms/bpm/set'
        },
        'alarm1': {
            'enabled': True,
            'broadcast_topic': 'shh/alarms/gpio1',
            'listen_topic': 'shh/alarms/gpio1/set'
        },
        'alarm2': {
            'enabled': True,
            'broadcast_topic': 'shh/alarms/gpio2',
            'listen_topic': 'shh/alarms/gpio2/set'
        }
    }

@app.post("/api/mqtt/settings")
async def save_mqtt_settings(settings: dict, db: Session = Depends(get_db)):
    """Save MQTT settings"""
    try:
        # Save basic MQTT settings with proper data types
        for key, value in settings.items():
            if key.startswith('mqtt_') and key != 'mqtt_topics':
                # Determine data type and save accordingly
                if isinstance(value, bool):
                    save_setting(db, key, value, 'bool')
                elif isinstance(value, int):
                    save_setting(db, key, value, 'int')  
                else:
                    save_setting(db, key, str(value), 'string')
        
        # Save topic configurations as JSON
        if 'topics' in settings:
            import json
            topics_json = json.dumps(settings['topics'])
            save_setting(db, 'mqtt_topics', topics_json, 'json')
        
        # Restart MQTT connection with new settings if MQTT is enabled
        restart_result = await restart_mqtt_if_enabled(db)
        
        return {"message": "MQTT settings saved successfully", "mqtt_restart": restart_result}
    except Exception as e:
        logger.error(f"Error saving MQTT settings: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error saving MQTT settings: {str(e)}"}
        )

async def restart_mqtt_if_enabled(db: Session):
    """Restart MQTT connection if enabled in settings"""
    global mqtt_client_ref
    
    try:
        # Check if MQTT is enabled
        mqtt_enabled = get_setting(db, 'mqtt_enabled', False)
        
        if not mqtt_enabled:
            # Disconnect existing client if any
            if mqtt_client_ref:
                try:
                    mqtt_client_ref.disconnect()
                    logger.info("[restart_mqtt] Disconnected MQTT client (disabled)")
                except:
                    pass
                mqtt_client_ref = None
            return "MQTT disabled - disconnected"
        
        # Disconnect existing client
        if mqtt_client_ref:
            try:
                mqtt_client_ref.disconnect()
                logger.info("[restart_mqtt] Disconnected existing MQTT client")
            except:
                pass
            mqtt_client_ref = None
        
        # Create new client with updated settings
        mqtt = get_mqtt_client(asyncio.get_event_loop())
        
        if mqtt:
            # Get MQTT settings from database
            from mqtt_handler import get_mqtt_settings
            mqtt_settings = get_mqtt_settings()
            
            # Connect using database settings
            mqtt.connect(mqtt_settings['broker'], mqtt_settings['port'], 60)
            logger.info(f"[restart_mqtt] Connected to MQTT broker at {mqtt_settings['broker']}:{mqtt_settings['port']}")

            # Send MQTT discovery if enabled
            discovery_enabled = get_setting(db, 'mqtt_discovery_enabled', True)
            test_mode = get_setting(db, 'mqtt_test_mode', True)
            
            if discovery_enabled:
                send_mqtt_discovery(mqtt, test_mode=test_mode)

            # Set availability to online using base topic from settings
            base_topic = get_setting(db, 'mqtt_base_topic', 'shh')
            mqtt.publish(f"{base_topic}/spo2/availability", "online", retain=True)
            logger.info(f"[restart_mqtt] Published online status to {base_topic}/spo2/availability")

            # Set the MQTT client in the state manager
            set_mqtt_client(mqtt)
            mqtt_client_ref = mqtt

            # Start the MQTT loop in a separate thread
            threading.Thread(target=mqtt.loop_forever, daemon=True).start()
            
            return "MQTT connection restarted successfully"
        else:
            return "MQTT connection failed - invalid settings"
            
    except Exception as e:
        logger.error(f"[restart_mqtt] Error restarting MQTT: {e}")
        return f"MQTT restart failed: {str(e)}"

@app.post("/api/mqtt/test-connection")
async def test_mqtt_connection(settings: dict):
    """Test MQTT connection with provided settings"""
    try:
        import paho.mqtt.client as mqtt
        import time
        
        test_client = mqtt.Client(client_id=settings.get('mqtt_client_id', 'test_client'))
        
        # Set credentials if provided
        username = settings.get('mqtt_username')
        password = settings.get('mqtt_password')
        if username and password:
            test_client.username_pw_set(username, password)
        
        connection_result = {"connected": False, "error": None}
        
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                connection_result["connected"] = True
            else:
                connection_result["error"] = f"Connection failed with code {rc}"
            client.disconnect()
        
        def on_disconnect(client, userdata, rc):
            pass
        
        test_client.on_connect = on_connect
        test_client.on_disconnect = on_disconnect
        
        # Try to connect
        broker = settings.get('mqtt_broker', 'localhost')
        port = int(settings.get('mqtt_port', 1883))
        
        test_client.connect(broker, port, 10)
        test_client.loop_start()
        
        # Wait for connection attempt
        time.sleep(2)
        test_client.loop_stop()
        
        if connection_result["connected"]:
            return {"status": "success", "message": "Successfully connected to MQTT broker"}
        else:
            error_msg = connection_result["error"] or "Connection failed"
            return JSONResponse(
                status_code=400,
                content={"detail": error_msg}
            )
            
    except Exception as e:
        logger.error(f"Error testing MQTT connection: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error testing MQTT connection: {str(e)}"}
        )

@app.post("/api/mqtt/send-discovery")
async def send_mqtt_discovery_endpoint(request: dict):
    """Send MQTT discovery messages to Home Assistant"""
    try:
        test_mode = request.get('test_mode', True)
        
        # Get the current MQTT client (if connected)
        global mqtt_client_ref
        if mqtt_client_ref and mqtt_client_ref.is_connected():
            send_mqtt_discovery(mqtt_client_ref, test_mode=test_mode)
            return {"message": "MQTT discovery messages sent successfully"}
        else:
            return JSONResponse(
                status_code=400,
                content={"detail": "MQTT client not connected"}
            )
            
    except Exception as e:
        logger.error(f"Error sending MQTT discovery: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error sending MQTT discovery: {str(e)}"}
        )


@app.get("/api/serial/log")
async def get_serial_log_endpoint():
    """Return the last raw serial lines for preview."""
    try:
        return {"lines": get_serial_log()}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/serial/status")
async def get_serial_status(db: Session = Depends(get_db)):
    """Return serial reader status and configured baud rate."""
    try:
        from crud import get_setting
        configured_baud = get_setting(db, "baud_rate", os.getenv("BAUD_RATE", 19200))
        try:
            configured_baud = int(configured_baud)
        except Exception:
            pass
        return {
            "serial_active": is_serial_mode(),
            "baud_rate": configured_baud
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# Pulse Ox History Analysis Endpoints

@app.get("/api/monitoring/history/dates")
async def get_available_dates(db: Session = Depends(get_db)):
    """Get list of dates that have pulse ox data"""
    from crud import get_available_pulse_ox_dates
    try:
        dates = get_available_pulse_ox_dates(db)
        return
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving available dates: {str(e)}")


@app.get("/api/monitoring/history/analyze/{date}")
async def analyze_pulse_ox_history(date: str, db: Session = Depends(get_db)):
    """Analyze pulse ox data for a specific date"""
    from crud import analyze_pulse_ox_day
    try:
        # Validate date format
        from datetime import datetime
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        analysis = analyze_pulse_ox_day(db, date)
        return analysis
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing pulse ox data: {str(e)}")


@app.get("/api/monitoring/history/raw/{date}")
async def get_raw_pulse_ox_data(date: str, db: Session = Depends(get_db)):
    """Get raw pulse ox data for a specific date"""
    from crud import get_pulse_ox_data_by_date
    try:
        # Validate date format
        from datetime import datetime
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        data = get_pulse_ox_data_by_date(db, date)
        
        # Convert to dictionaries for JSON response
        result = []
        for reading in data:
            result.append({
                'id': reading.id,
                'timestamp': reading.timestamp.isoformat() if reading.timestamp else None,
                'spo2': reading.spo2,
                'bpm': reading.bpm,
                'pa': reading.pa,
                'status': reading.status,
                'motion': reading.motion,
                'spo2_alarm': reading.spo2_alarm,
                'hr_alarm': reading.hr_alarm
            })
        
        return {
            'date': date,
            'readings': result,
            'count': len(result)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving raw pulse ox data: {str(e)}")
