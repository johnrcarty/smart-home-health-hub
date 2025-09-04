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
from mqtt import MQTTManager, MQTTPublisher, create_message_handlers, send_mqtt_discovery
from state_manager import (
    set_event_loop, set_mqtt_publisher, reset_sensor_state, update_sensor,
    register_websocket_client, unregister_websocket_client
)
from db import get_db
from crud import get_setting, save_setting

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

# Store references to MQTT components for shutdown
mqtt_client_ref = None
mqtt_manager = None
mqtt_publisher = None

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
    global mqtt_client_ref, mqtt_manager, mqtt_publisher

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
    mqtt_manager = MQTTManager(loop)
    mqtt_publisher = MQTTPublisher()
    
    # Create message handlers for incoming MQTT messages
    message_handlers = create_message_handlers(update_sensor)
    for vital_type, handler in message_handlers.items():
        mqtt_manager.set_message_handler(vital_type, handler)
    
    # Create and connect MQTT client if enabled
    mqtt_client = mqtt_manager.create_client()
    mqtt_client_ref = mqtt_client  # Store reference for shutdown

    if mqtt_client:  # Only proceed if MQTT is enabled and configured
        try:
            # Connect to MQTT broker
            if mqtt_manager.connect():
                logger.info("[main] Connected to MQTT broker")
                
                # Set up the publisher with the client
                mqtt_publisher.set_client(mqtt_client)
                
                # Send MQTT discovery if enabled
                discovery_enabled = get_setting(db, 'mqtt_discovery_enabled', True)
                test_mode = get_setting(db, 'mqtt_test_mode', True)
                
                if discovery_enabled:
                    send_mqtt_discovery(mqtt_client, test_mode=test_mode)

                # Set availability to online using base topic from settings
                from mqtt.settings import get_mqtt_settings
                mqtt_settings = get_mqtt_settings()
                base_topic = mqtt_settings.get('base_topic', 'shh')
                mqtt_client.publish(f"{base_topic}/availability", "online", retain=True)
                logger.info(f"[main] Published online status to {base_topic}/availability")

                # Set the MQTT publisher in the state manager
                set_mqtt_publisher(mqtt_publisher)
            else:
                logger.error("[main] Failed to connect to MQTT broker")
        except Exception as e:
            logger.error(f"[main] Failed to initialize MQTT: {e}")
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
    # Use the global references
    global mqtt_client_ref, mqtt_manager

    if mqtt_client_ref:
        try:
            # Get base topic from settings for proper offline message
            db = next(get_db())
            from mqtt.settings import get_mqtt_settings
            mqtt_settings = get_mqtt_settings()
            base_topic = mqtt_settings.get('base_topic', 'shh')
            db.close()
            
            mqtt_client_ref.publish(f"{base_topic}/availability", "offline", retain=True)
            logger.info(f"[main] Published offline status to {base_topic}/availability")

            # Properly disconnect using the manager
            if mqtt_manager:
                mqtt_manager.disconnect()
            else:
                mqtt_client_ref.disconnect()
        except Exception as e:
            logger.error(f"[main] Failed to publish offline status: {e}")
    else:
        logger.info("[main] No MQTT client to disconnect")
