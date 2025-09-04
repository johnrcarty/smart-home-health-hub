import threading
from serial_reader import serial_loop
import asyncio
import json  # Add this import
import platform
import logging
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Import route modules
from routes import core, settings, vitals, medications, care_tasks, equipment, monitoring, mqtt, serial

# Import core components
from mqtt import initialize_mqtt_service, shutdown_mqtt_service
from state_manager import (
    set_event_loop, set_mqtt_publisher, reset_sensor_state, update_sensor,
    register_websocket_client, unregister_websocket_client
)
from db import get_db
from crud.settings import get_setting, save_setting

load_dotenv()

# Initialize a logger for your application
logger = logging.getLogger("app")

# Configure logging
logging.basicConfig(level=logging.INFO)

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

# FastAPI app setup
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register route modules
app.include_router(core.router)
app.include_router(settings.router)
app.include_router(vitals.router)
app.include_router(medications.router)
app.include_router(care_tasks.router)
app.include_router(equipment.router)
app.include_router(monitoring.router)
app.include_router(mqtt.router)
app.include_router(serial.router)

loop = asyncio.get_event_loop()


@app.on_event("startup")
async def startup_event():
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

    # 1) Initialize MQTT system
    mqtt_manager, mqtt_publisher = initialize_mqtt_service(loop, update_sensor)
    
    if mqtt_manager and mqtt_publisher:
        logger.info("[main] MQTT system initialized successfully")
        # Set the MQTT publisher in the state manager
        set_mqtt_publisher(mqtt_publisher)
    else:
        logger.info("[main] MQTT system not initialized (disabled or failed)")

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
    # Shutdown MQTT service
    shutdown_mqtt_service()
