# state_manager.py

import asyncio
import json
from sensor_manager import SENSOR_DEFINITIONS
import os
from crud import get_last_n_blood_pressure, get_last_n_temperature
from datetime import datetime
import time
from collections import deque
from contextlib import contextmanager
from db import get_db

# Database session wrapper for state_manager
@contextmanager
def get_db_session():
    """Context manager for database sessions in state_manager"""
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()

MIN_SPO2 = int(os.getenv("MIN_SPO2", 90))
MAX_SPO2 = int(os.getenv("MAX_SPO2", 100))
MIN_BPM = int(os.getenv("MIN_BPM", 55))
MAX_BPM = int(os.getenv("MAX_BPM", 155))


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

from crud import get_unacknowledged_alerts_count, save_pulse_ox_data, start_monitoring_alert, update_monitoring_alert, save_pulse_ox_batch
from models import PulseOxData

# Add these global variables to track the current alert state
current_alert_id = None
alert_thresholds_exceeded = False
alert_start_data_id = None

# Add these global variables to track recovery timing
alert_recovery_start_time = None
RECOVERY_SECONDS_REQUIRED = 30  # Require 30 seconds of good readings to end an alert

# Add these global variables for caching pulse ox data
pulse_ox_cache = deque(maxlen=150)  # ~30 seconds at 5Hz sample rate
event_data_points = []  # Store all data points during an event
CACHE_DURATION_SECONDS = 30  # How many seconds of data to keep in normal operation

# Add batch processing variables for continuous data logging
pulse_ox_batch_buffer = []  # Buffer for batching pulse ox data
batch_start_time = None
BATCH_DURATION_SECONDS = 30  # Save data every 30 seconds

# Add this global variable near the top
alarm_states = {"alarm1": False, "alarm2": False}

# Add these global variables near your other alert state variables
alarm_event_active = False
alarm_event_start_time = None
alarm_event_data_points = []

# Buffer last N raw serial lines for preview in UI
serial_log = deque(maxlen=30)

def get_serial_log():
    """Return the current serial log as a list."""
    return list(serial_log)

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

def publish_to_mqtt():
    """
    Publish current sensor state to configured MQTT topics based on database settings.
    """
    global mqtt_client  # Declare global at the top
    
    # Get MQTT settings from database first to check if enabled
    from crud import get_setting
    from db import SessionLocal
    
    # Create a database session for getting settings
    db = SessionLocal()
    try:
        # Check if MQTT is enabled first
        mqtt_enabled = get_setting(db, 'mqtt_enabled', False)
        if not mqtt_enabled:
            print("[state_manager] MQTT is disabled, skipping publish.")
            return
        
        # Check if MQTT client is set
        if not mqtt_client:
            print("[state_manager] MQTT client not available, skipping publish.")
            print("[state_manager] This usually means MQTT is disabled or failed to initialize in main.py")
            return
        
        # Check if MQTT client is connected
        try:
            if not mqtt_client.is_connected():
                print("[state_manager] MQTT client is not connected. This may cause publish failures.")
                # Note: We don't attempt to reconnect here since the main MQTT client should handle reconnection
        except Exception as e:
            error_msg = f"MQTT connection check failed: {str(e)}"
            print(f"[state_manager] {error_msg}")
            return
        
        # Get topics configuration
        topics_json = get_setting(db, 'mqtt_topics')
        if not topics_json:
            print("[state_manager] No MQTT topics configuration found.")
            return
        
        try:
            topics = json.loads(topics_json) if isinstance(topics_json, str) else topics_json
        except (json.JSONDecodeError, TypeError) as e:
            error_msg = f"Error parsing MQTT topics configuration: {str(e)}"
            print(f"[state_manager] {error_msg}")
            return

        # Get MQTT client ID for origin tracking
        mqtt_client_id = get_setting(db, 'mqtt_client_id', 'sensor_monitor')
        
        timestamp = datetime.now().strftime("%y-%b-%d %H:%M:%S")
        published_count = 0
        
        # Publish pulse ox data (SpO2, BPM, Perfusion)
        if topics.get('spo2', {}).get('enabled', False):
            try:
                # Only publish if we have actual pulse ox data
                if (sensor_state.get("spo2") is not None or 
                    sensor_state.get("bpm") is not None or 
                    sensor_state.get("perfusion") is not None):
                    
                    # Status to motion conversion
                    motion = "OFF"
                    if sensor_state["status"] is not None:
                        motion = "ON" if "MO" in str(sensor_state["status"]) else "OFF"

                    # Alarm Logic
                    spo2_alarm = "OFF"
                    if sensor_state["spo2"] is not None:
                        try:
                            spo2_alarm = "ON" if not (MIN_SPO2 <= int(sensor_state["spo2"]) <= MAX_SPO2) else "OFF"
                        except (ValueError, TypeError):
                            spo2_alarm = "OFF"

                    hr_alarm = "OFF"
                    if sensor_state["bpm"] is not None:
                        try:
                            hr_alarm = "ON" if not (MIN_BPM <= int(sensor_state["bpm"]) <= MAX_BPM) else "OFF"
                        except (ValueError, TypeError):
                            hr_alarm = "OFF"

                    payload = {
                        "timestamp": timestamp,
                        "spo2": sensor_state["spo2"],
                        "bpm": sensor_state["bpm"],
                        "pa": sensor_state["perfusion"],
                        "status": sensor_state["status"],
                        "motion": motion,
                        "spo2_alarm": spo2_alarm,
                        "hr_alarm": hr_alarm,
                        "origin": mqtt_client_id
                    }

                    broadcast_topic = topics['spo2'].get('broadcast_topic', 'shh/spo2/state')
                    json_payload = json.dumps(payload)
                    result = mqtt_client.publish(broadcast_topic, json_payload, retain=True)
                    
                    if result.rc == 0:
                        print(f"[state_manager] Published SpO2 data to {broadcast_topic}: {json_payload}")
                        published_count += 1
                    else:
                        print(f"[state_manager] Failed to publish SpO2 data to {broadcast_topic}, result code: {result.rc}")
                else:
                    print("[state_manager] Skipping SpO2 MQTT publish - no pulse ox data available")
                    
            except Exception as e:
                error_msg = f"Error publishing SpO2 data to MQTT: {str(e)}"
                print(f"[state_manager] {error_msg}")
        
        # Publish temperature data
        if topics.get('temperature', {}).get('enabled', False):
            try:
                # Get the latest temperature reading
                from crud import get_last_n_temperature
                temp_data = get_last_n_temperature(db, 1)
                
                if temp_data and len(temp_data) > 0:
                    latest_temp = temp_data[0]
                    # Only publish if we have actual temperature data
                    if (latest_temp.get('skin_temp') is not None or 
                        latest_temp.get('body_temp') is not None):
                        
                        temp_payload = {
                            "timestamp": timestamp,
                            "skin_temp": latest_temp.get('skin_temp'),
                            "body_temp": latest_temp.get('body_temp'),
                            "datetime": latest_temp.get('datetime').isoformat() if latest_temp.get('datetime') else None,
                            "origin": mqtt_client_id
                        }

                        broadcast_topic = topics['temperature'].get('broadcast_topic', 'shh/temp/state')
                        json_payload = json.dumps(temp_payload, default=str)
                        result = mqtt_client.publish(broadcast_topic, json_payload, retain=True)
                        
                        if result.rc == 0:
                            print(f"[state_manager] Published temperature data to {broadcast_topic}: {json_payload}")
                            published_count += 1
                        else:
                            print(f"[state_manager] Failed to publish temperature data to {broadcast_topic}, result code: {result.rc}")
                    else:
                        print("[state_manager] Skipping temperature MQTT publish - no temperature data available")
                else:
                    print("[state_manager] Skipping temperature MQTT publish - no temperature readings found")
                        
            except Exception as e:
                error_msg = f"Error publishing temperature data to MQTT: {str(e)}"
                print(f"[state_manager] {error_msg}")
        
        # Publish blood pressure data
        if topics.get('blood_pressure', {}).get('enabled', False):
            try:
                # Get the latest blood pressure reading
                from crud import get_last_n_blood_pressure
                bp_data = get_last_n_blood_pressure(db, 1)
                
                if bp_data and len(bp_data) > 0:
                    latest_bp = bp_data[0]
                    # Only publish if we have actual blood pressure data
                    if (latest_bp.get('systolic_bp') is not None or 
                        latest_bp.get('diastolic_bp') is not None or 
                        latest_bp.get('map_bp') is not None):
                        
                        bp_payload = {
                            "timestamp": timestamp,
                            "systolic": latest_bp.get('systolic_bp'),
                            "diastolic": latest_bp.get('diastolic_bp'),
                            "map": latest_bp.get('map_bp'),
                            "datetime": latest_bp.get('datetime').isoformat() if latest_bp.get('datetime') else None,
                            "origin": mqtt_client_id
                        }

                        broadcast_topic = topics['blood_pressure'].get('broadcast_topic', 'shh/bp/state')
                        json_payload = json.dumps(bp_payload, default=str)
                        result = mqtt_client.publish(broadcast_topic, json_payload, retain=True)
                        
                        if result.rc == 0:
                            print(f"[state_manager] Published blood pressure data to {broadcast_topic}: {json_payload}")
                            published_count += 1
                        else:
                            print(f"[state_manager] Failed to publish blood pressure data to {broadcast_topic}, result code: {result.rc}")
                    else:
                        print("[state_manager] Skipping blood pressure MQTT publish - no blood pressure data available")
                else:
                    print("[state_manager] Skipping blood pressure MQTT publish - no blood pressure readings found")
                        
            except Exception as e:
                error_msg = f"Error publishing blood pressure data to MQTT: {str(e)}"
                print(f"[state_manager] {error_msg}")

        if published_count > 0:
            print(f"[state_manager] Successfully published {published_count} MQTT messages")
        else:
            print("[state_manager] No MQTT messages were published (no enabled topics or no data)")
        
    finally:
        db.close()


def publish_specific_vital_to_mqtt(vital_type, vital_data):
    """
    Publish a specific vital type to MQTT based on database settings.
    
    Args:
        vital_type: The type of vital (e.g., 'bathroom', 'temperature', 'blood_pressure')
        vital_data: The data to publish (dict)
    """
    print(f"[state_manager] publish_specific_vital_to_mqtt called for {vital_type} with data: {vital_data}")
    global mqtt_client
    
    # Get MQTT settings from database first to check if enabled
    from crud import get_setting
    from db import SessionLocal
    
    # Create a database session for getting settings
    db = SessionLocal()
    try:
        # Check if MQTT is enabled first
        mqtt_enabled = get_setting(db, 'mqtt_enabled', False)
        if not mqtt_enabled:
            print(f"[state_manager] MQTT is disabled, skipping {vital_type} publish.")
            return
        
        # Check if MQTT client is set, if not, skip publishing since main.py should have set it
        if not mqtt_client:
            print(f"[state_manager] MQTT client not available for {vital_type}, skipping publish.")
            print(f"[state_manager] This usually means MQTT is disabled or failed to initialize in main.py")
            return
        
        # Check if MQTT client is connected
        if not mqtt_client.is_connected():
            print(f"[state_manager] MQTT client is not connected for {vital_type}. This may cause publish failures.")
            # Note: We don't attempt to reconnect here since the main MQTT client should handle reconnection
        
        # Get topics configuration
        topics_json = get_setting(db, 'mqtt_topics')
        if not topics_json:
            print(f"[state_manager] No MQTT topics configuration found for {vital_type}.")
            return
        
        try:
            topics = json.loads(topics_json) if isinstance(topics_json, str) else topics_json
        except (json.JSONDecodeError, TypeError) as e:
            print(f"[state_manager] Error parsing MQTT topics configuration: {str(e)}")
            return

        # Check if this specific vital type is enabled for MQTT
        if not topics.get(vital_type, {}).get('enabled', False):
            print(f"[state_manager] MQTT publishing for {vital_type} is disabled.")
            return

        # Get MQTT client ID for origin tracking
        mqtt_client_id = get_setting(db, 'mqtt_client_id', 'sensor_monitor')
        
        timestamp = datetime.now().strftime("%y-%b-%d %H:%M:%S")
        
        # Create payload based on vital type
        if vital_type == 'bathroom':
            # Handle datetime formatting safely
            datetime_val = vital_data.get('datetime')
            formatted_datetime = None
            if datetime_val:
                if hasattr(datetime_val, 'isoformat'):
                    formatted_datetime = datetime_val.isoformat()
                else:
                    formatted_datetime = str(datetime_val)
            
            payload = {
                "timestamp": timestamp,
                "type": vital_data.get('bathroom_type'),
                "size": vital_data.get('bathroom_size'),
                "value": vital_data.get('value'),
                "datetime": formatted_datetime,
                "notes": vital_data.get('notes'),
                "origin": mqtt_client_id
            }
        elif vital_type == 'temperature':
            # Handle datetime formatting safely
            datetime_val = vital_data.get('datetime')
            formatted_datetime = None
            if datetime_val:
                if hasattr(datetime_val, 'isoformat'):
                    formatted_datetime = datetime_val.isoformat()
                else:
                    formatted_datetime = str(datetime_val)
            
            payload = {
                "timestamp": timestamp,
                "skin_temp": vital_data.get('skin_temp'),
                "body_temp": vital_data.get('body_temp'),
                "datetime": formatted_datetime,
                "origin": mqtt_client_id
            }
        elif vital_type == 'blood_pressure':
            # Handle datetime formatting safely
            datetime_val = vital_data.get('datetime')
            formatted_datetime = None
            if datetime_val:
                if hasattr(datetime_val, 'isoformat'):
                    formatted_datetime = datetime_val.isoformat()
                else:
                    formatted_datetime = str(datetime_val)
            
            payload = {
                "timestamp": timestamp,
                "systolic": vital_data.get('systolic_bp'),
                "diastolic": vital_data.get('diastolic_bp'),
                "map": vital_data.get('map_bp'),
                "datetime": formatted_datetime,
                "origin": mqtt_client_id
            }
        elif vital_type in ['nutrition', 'water', 'calories']:
            # Handle nutrition vitals
            # Handle datetime formatting safely
            datetime_val = vital_data.get('datetime')
            formatted_datetime = None
            if datetime_val:
                if hasattr(datetime_val, 'isoformat'):
                    formatted_datetime = datetime_val.isoformat()
                else:
                    formatted_datetime = str(datetime_val)
            
            if vital_type == 'nutrition':
                # For nutrition, we might have both water and calories
                payload = {
                    "timestamp": timestamp,
                    "water": vital_data.get('water'),
                    "calories": vital_data.get('calories'),
                    "datetime": formatted_datetime,
                    "origin": mqtt_client_id
                }
            else:
                payload = {
                    "timestamp": timestamp,
                    "value": vital_data.get('value'),
                    "datetime": formatted_datetime,
                    "notes": vital_data.get('notes'),
                    "origin": mqtt_client_id
                }
        else:
            # Generic vital payload
            # Handle datetime formatting safely
            datetime_val = vital_data.get('datetime')
            formatted_datetime = None
            if datetime_val:
                if hasattr(datetime_val, 'isoformat'):
                    formatted_datetime = datetime_val.isoformat()
                else:
                    formatted_datetime = str(datetime_val)
            
            payload = {
                "timestamp": timestamp,
                "value": vital_data.get('value'),
                "vital_type": vital_type,
                "datetime": formatted_datetime,
                "notes": vital_data.get('notes'),
                "origin": mqtt_client_id
            }

        # Get the broadcast topic
        broadcast_topic = topics[vital_type].get('broadcast_topic', f'shh/{vital_type}/state')
        json_payload = json.dumps(payload, default=str)
        
        print(f"[state_manager] About to publish to MQTT: topic={broadcast_topic}, payload={json_payload}")
        
        # Publish to MQTT (removed retain=True temporarily to test duplication)
        result = mqtt_client.publish(broadcast_topic, json_payload, retain=False)
        
        print(f"[state_manager] MQTT publish result: rc={result.rc}, mid={result.mid}")
        
        if result.rc == 0:
            print(f"[state_manager] Published {vital_type} data to {broadcast_topic}: {json_payload}")
        else:
            print(f"[state_manager] Failed to publish {vital_type} data to {broadcast_topic}, result code: {result.rc}")
            
    except Exception as e:
        error_msg = f"Error publishing {vital_type} data to MQTT: {str(e)}"
        print(f"[state_manager] {error_msg}")
    finally:
        db.close()
def check_thresholds(spo2, bpm):
    """Check if SpO2 or BPM are outside acceptable ranges.
    
    Returns:
        tuple: (spo2_alarm, hr_alarm) boolean flags
    """
    from crud import get_setting
    
    # Get threshold settings, ensuring they're integers
    min_spo2 = int(get_setting('min_spo2', 90))
    max_spo2 = int(get_setting('max_spo2', 100))
    min_bpm = int(get_setting('min_bpm', 55))
    max_bpm = int(get_setting('max_bpm', 155))
    
    spo2_alarm = False
    hr_alarm = False
    
    # Only check if we have valid data
    if spo2 is not None:
        # Make sure spo2 is an integer for comparison
        if isinstance(spo2, str) and spo2.isdigit():
            spo2 = int(spo2)
        
        if isinstance(spo2, (int, float)):
            spo2_alarm = spo2 < min_spo2 or spo2 > max_spo2
    
    if bpm is not None:
        # Make sure bpm is an integer for comparison
        if isinstance(bpm, str) and bpm.isdigit():
            bpm = int(bpm)
            
        if isinstance(bpm, (int, float)):
            hr_alarm = bpm < min_bpm or bpm > max_bpm
    
    if spo2_alarm or hr_alarm:
        print(f"[state_manager] ALERT! SpO2: {spo2} (threshold: {min_spo2}-{max_spo2}), "
              f"HR: {bpm} (threshold: {min_bpm}-{max_bpm})")
    
    return spo2_alarm, hr_alarm


def broadcast_state():
    """
    Send the full `sensor_state` snapshot over WebSockets to all clients.
    Include alert counts, BP readings, temperature readings, and settings.
    """
    if not event_loop:
        print("[state_manager] Cannot broadcast, event_loop not set.")
        return

    # Get the last 5 blood pressure readings
    with get_db_session() as db:
        bp_history = get_last_n_blood_pressure(db, 5)
        temp_history = get_last_n_temperature(db, 5)
        from crud import get_all_settings, get_unacknowledged_alerts_count, get_equipment_due_count, get_due_and_upcoming_medications_count
        settings = get_all_settings(db)
        alerts_count = get_unacknowledged_alerts_count(db)
        equipment_due_count = get_equipment_due_count(db)
        medications_due_count = get_due_and_upcoming_medications_count(db)
    
    # Create a clean copy of the current state with only proper keys
    state_copy = {}
    for key, value in sensor_state.items():
        # Only include string keys that are actual sensor names (not tuples)
        if isinstance(key, str):
            state_copy[key] = value
    
    # Add histories and other data
    state_copy['bp'] = bp_history
    state_copy['temp'] = temp_history
    state_copy['settings'] = settings
    state_copy['alerts_count'] = alerts_count
    state_copy['equipment_due_count'] = equipment_due_count
    state_copy['medications'] = medications_due_count
    
    # Ensure all standard values have defaults
    for key in ['spo2', 'bpm', 'perfusion', 'status', 'map_bp']:
        if key not in state_copy or state_copy[key] is None:
            state_copy[key] = -1  # Use -1 as sentinel value

    # Add alarm states to the state_copy dict
    state_copy['alarm1'] = alarm_states.get('alarm1', False)
    state_copy['alarm2'] = alarm_states.get('alarm2', False)

    # --- Add spo2_alarm and bpm_alarm ---
    # Get thresholds from settings
    min_spo2 = int(settings.get('min_spo2', {}).get('value', 90))
    max_spo2 = int(settings.get('max_spo2', {}).get('value', 100))
    min_bpm = int(settings.get('min_bpm', {}).get('value', 55))
    max_bpm = int(settings.get('max_bpm', {}).get('value', 155))

    spo2_val = state_copy.get('spo2', -1)
    bpm_val = state_copy.get('bpm', -1)

    state_copy['spo2_alarm'] = False
    state_copy['bpm_alarm'] = False

    if isinstance(spo2_val, (int, float)) and spo2_val != -1:
        if spo2_val < min_spo2 or spo2_val > max_spo2:
            state_copy['spo2_alarm'] = True

    if isinstance(bpm_val, (int, float)) and bpm_val != -1:
        if bpm_val < min_bpm or bpm_val > max_bpm:
            state_copy['bpm_alarm'] = True
    # --- End addition ---

    # Add combined alarm field
    state_copy['alarm'] = (
        state_copy['alarm1'] or
        state_copy['alarm2'] or
        state_copy['spo2_alarm'] or
        state_copy['bpm_alarm']
    )

    # Add dynamic chart data based on settings
    chart_1_vital = settings.get('dashboard_chart_1_vital', {}).get('value', 'bp')
    chart_2_vital = settings.get('dashboard_chart_2_vital', {}).get('value', 'temperature')
    
    # Get data for the configured dashboard charts
    chart_1_data = []
    chart_2_data = []
    
    if chart_1_vital:
        if chart_1_vital == 'bp':
            chart_1_data = bp_history
        elif chart_1_vital == 'temperature':
            # Transform temperature data to match expected format
            chart_1_data = [
                {
                    'datetime': reading.get('datetime'),
                    'skin': reading.get('skin_temp'),
                    'body': reading.get('body_temp')
                }
                for reading in temp_history
                if reading.get('skin_temp') is not None or reading.get('body_temp') is not None
            ]
        else:
            # Get from vitals table - need to fetch this dynamically
            try:
                with get_db_session() as db:
                    from crud import get_vitals_by_type
                    chart_1_data = get_vitals_by_type(db, chart_1_vital, 5)
            except Exception as e:
                print(f"[state_manager] Error fetching chart 1 data for {chart_1_vital}: {e}")
                chart_1_data = []
    
    if chart_2_vital and chart_2_vital != chart_1_vital:  # Ensure no duplication
        if chart_2_vital == 'bp':
            chart_2_data = bp_history
        elif chart_2_vital == 'temperature':
            # Transform temperature data to match expected format
            chart_2_data = [
                {
                    'datetime': reading.get('datetime'),
                    'skin': reading.get('skin_temp'),
                    'body': reading.get('body_temp')
                }
                for reading in temp_history
                if reading.get('skin_temp') is not None or reading.get('body_temp') is not None
            ]
        else:
            # Get from vitals table - need to fetch this dynamically
            try:
                with get_db_session() as db:
                    from crud import get_vitals_by_type
                    chart_2_data = get_vitals_by_type(db, chart_2_vital, 5)
            except Exception as e:
                print(f"[state_manager] Error fetching chart 2 data for {chart_2_vital}: {e}")
                chart_2_data = []
    
    state_copy['dashboard_chart_1'] = {
        'vital_type': chart_1_vital,
        'data': chart_1_data
    }
    state_copy['dashboard_chart_2'] = {
        'vital_type': chart_2_vital,
        'data': chart_2_data
    }

    print(f"[state_manager] Clean state to broadcast: {state_copy}")
    
    # Serialize datetime objects to strings before sending
    serialized_state = serialize_datetime_objects(state_copy)
    
    print(f"[state_manager] Broadcasting to {len(websocket_clients)} clients.")
    message = {
        "type": "sensor_update",
        "state": serialized_state
    }
    
    for ws in list(websocket_clients):
        try:
            asyncio.run_coroutine_threadsafe(ws.send_json(message), event_loop)
        except Exception as e:
            print(f"[state_manager] Failed to send to websocket: {e}")
            websocket_clients.discard(ws)

    # Call alarm event state updater
    update_alarm_event_state()

def broadcast_serial_raw(raw_data):
    """
    Broadcast raw serial data to WebSocket clients for debugging/monitoring purposes.
    
    Args:
        raw_data (str): Raw serial line data
    """
    if not event_loop:
        print("[state_manager] Cannot broadcast raw serial, event_loop not set.")
        return
    
    if not websocket_clients:
        return  # No clients to send to
    
    message = {
        "type": "serial_raw",
        "data": raw_data,
        "timestamp": datetime.now().isoformat()
    }
    
    # Send to all connected WebSocket clients using same pattern as broadcast_state
    for ws in list(websocket_clients):
        try:
            asyncio.run_coroutine_threadsafe(ws.send_json(message), event_loop)
        except Exception as e:
            print(f"[state_manager] Failed to send raw serial to websocket: {e}")
            websocket_clients.discard(ws)

def update_sensor(*updates, from_mqtt=False):
    """
    Update sensor state values, track alerts, and broadcast changes
    
    Args:
        *updates: Either pairs of (sensor_name, value) or a list of (name, value) tuples
        from_mqtt: Whether this update is from MQTT (vs serial)
    """
    global current_alert_id, alert_thresholds_exceeded, alert_start_data_id, sensor_state
    global alert_recovery_start_time, pulse_ox_cache, event_data_points
    
    has_pulse_ox_updates = False
    pulse_ox_data = {
        'spo2': None,
        'bpm': None,
        'perfusion': None,
        'status': None
    }
    
    updated = {}  # Track what's been updated for MQTT publishing
    raw_data = None
    current_time = datetime.now().isoformat()
    
    # Debug the incoming updates to see what we're getting
    print(f"[state_manager] Received updates: {updates}")
    
    # Handle the way serial_reader.py is calling this function
    # It sends: ([('spo2', 99), ('bpm', 91), ('perfusion', 4.0)], 'raw_data', '25-Jul-06 21:15:30    99      91       4')
    if len(updates) >= 3 and updates[1] == 'raw_data' and isinstance(updates[0], (list, tuple)):
        pairs = updates[0]
        raw_data = updates[2]
        
        for name, value in pairs:
            if name != "raw_data":
                sensor_state[name] = value  # Direct assignment with name as key
                updated[name] = value
                
                if name in pulse_ox_data:
                    pulse_ox_data[name] = value
                    has_pulse_ox_updates = True
    
    # Process updates based on how they're passed - keep existing handlers too
    elif len(updates) == 1 and isinstance(updates[0], (list, tuple)) and all(isinstance(x, tuple) for x in updates[0]):
        # Handle case where a list/tuple of (name, value) pairs is passed
        pairs = updates[0]
        
        # Look for raw_data separately
        raw_data_items = [pair[1] for pair in pairs if pair[0] == "raw_data"]
        if raw_data_items:
            raw_data = raw_data_items[0]
            
        # Process normal sensor values
        for name, value in pairs:
            if name != "raw_data":
                sensor_state[name] = value  # Direct assignment with name as key
                updated[name] = value
                
                if name in pulse_ox_data:
                    pulse_ox_data[name] = value
                    has_pulse_ox_updates = True
    else:
        # Handle case where name, value are passed as separate arguments
        for i in range(0, len(updates), 2):
            if i+1 < len(updates):  # Make sure we have a pair
                sensor_name = updates[i]
                value = updates[i+1]
                
                if sensor_name == "raw_data":
                    raw_data = value
                    continue
                    
                # Direct assignment with name as key
                sensor_state[sensor_name] = value  
                updated[sensor_name] = value
                
                # Track pulse ox related updates
                if sensor_name in pulse_ox_data:
                    pulse_ox_data[sensor_name] = value
                    has_pulse_ox_updates = True
    
    # Print current state for debugging (after fixing it)
    print(f"[state_manager] Current sensor state after update: {sensor_state}")
    
    # If no updates, exit early
    if not updated:
        print("[state_manager] No updates to process")
        return

    # If we received pulse ox data, cache it and check for alerts
    if has_pulse_ox_updates and (pulse_ox_data['spo2'] is not None or pulse_ox_data['bpm'] is not None):
        # Cache the current pulse ox data point
        data_point = {
            'timestamp': current_time,
            'spo2': pulse_ox_data['spo2'],
            'bpm': pulse_ox_data['bpm'],
            'perfusion': pulse_ox_data['perfusion'],
            'status': pulse_ox_data['status'],
            'motion': "ON" if sensor_state.get("motion", False) else "OFF",
            'raw_data': raw_data
        }
        
        # Always add to the rolling cache
        pulse_ox_cache.append(data_point)
        
        # Check if values exceed thresholds
        spo2_alarm, hr_alarm = check_thresholds(pulse_ox_data['spo2'], pulse_ox_data['bpm'])
        
        # Add alarm status to the data point
        data_point['spo2_alarm'] = "ON" if spo2_alarm else "OFF"
        data_point['hr_alarm'] = "ON" if hr_alarm else "OFF"
        
        # Save data to the continuous log
        data_id = save_pulse_ox_data(
            spo2=pulse_ox_data['spo2'], 
            bpm=pulse_ox_data['bpm'],
            pa=pulse_ox_data['perfusion'],
            status=pulse_ox_data['status'],
            motion="ON" if sensor_state.get("motion", False) else "OFF",
            spo2_alarm="ON" if spo2_alarm else "OFF",
            hr_alarm="ON" if hr_alarm else "OFF",
            raw_data=json.dumps(pulse_ox_data)
        )
        
        # Update the data point with the DB ID
        data_point['db_id'] = data_id
        
        # Check if we need to start or update an alert
        is_alert_condition = spo2_alarm or hr_alarm
        
        if is_alert_condition and not alert_thresholds_exceeded:
            # We've just crossed the threshold, start a new alert
            alert_thresholds_exceeded = True
            alert_recovery_start_time = None  # Reset recovery timer
            alert_start_data_id = data_id
            
            # Clear the event data points and add all cached points from before the event
            event_data_points = list(pulse_ox_cache)
            print(f"[state_manager] Alert started. Including {len(event_data_points)} cached data points.")
            
            # Start a new monitoring alert
            current_alert_id = start_monitoring_alert(
                spo2=pulse_ox_data['spo2'],
                bpm=pulse_ox_data['bpm'],
                data_id=data_id,
                spo2_alarm_triggered=1 if spo2_alarm else 0,
                hr_alarm_triggered=1 if hr_alarm else 0
            )
            
        elif is_alert_condition and alert_thresholds_exceeded and current_alert_id:
            # Continuing alert, update min/max values
            alert_recovery_start_time = None  # Reset recovery timer if we're in alert condition
            
            # Add this data point to our event collection
            event_data_points.append(data_point)
            
            update_monitoring_alert(
                alert_id=current_alert_id,
                spo2=pulse_ox_data['spo2'],
                bpm=pulse_ox_data['bpm'],
                spo2_alarm_triggered=1 if spo2_alarm else None,
                hr_alarm_triggered=1 if hr_alarm else None
            )
            
        elif not is_alert_condition and alert_thresholds_exceeded and current_alert_id:
            # Values are now within normal range, but we're still in an alert state
            # Start or continue tracking recovery time
            current_time_obj = datetime.now()
            
            # Add this data point to our event collection
            event_data_points.append(data_point)
            
            if alert_recovery_start_time is None:
                # First good reading after an alert, start recovery timer
                alert_recovery_start_time = time.time()
                print(f"[state_manager] Alert recovery started at {datetime.fromtimestamp(alert_recovery_start_time).isoformat()}")
                
                # Still update the min/max values during recovery period
                update_monitoring_alert(
                    alert_id=current_alert_id,
                    spo2=pulse_ox_data['spo2'],
                    bpm=pulse_ox_data['bpm']
                )
            elif (time.time() - alert_recovery_start_time) >= RECOVERY_SECONDS_REQUIRED:
                # We've had good readings for the required duration, finalize the alert
                now = current_time_obj.isoformat()
                print(f"[state_manager] Alert recovery completed after {RECOVERY_SECONDS_REQUIRED} seconds at {now}")
                
                update_monitoring_alert(
                    alert_id=current_alert_id,
                    end_time=now,
                    end_data_id=data_id,
                    spo2=pulse_ox_data['spo2'],
                    bpm=pulse_ox_data['bpm']
                )
                
                # Alert has ended, collect event data
                print(f"[state_manager] Alert ended. Collecting {len(event_data_points)} data points for the event.")
                
                # Add the event data to the alert record in DB
                store_event_data_for_alert(current_alert_id, event_data_points)
                
                # Reset alert state
                alert_thresholds_exceeded = False
                current_alert_id = None
                alert_recovery_start_time = None
                event_data_points = []
            else:
                # Still in recovery period, update the alert but don't end it yet
                elapsed = time.time() - alert_recovery_start_time
                remaining = RECOVERY_SECONDS_REQUIRED - elapsed
                print(f"[state_manager] Alert recovery in progress: {elapsed:.1f}s elapsed, {remaining:.1f}s remaining")
                
                # Update min/max values during recovery period
                update_monitoring_alert(
                    alert_id=current_alert_id,
                    spo2=pulse_ox_data['spo2'],
                    bpm=pulse_ox_data['bpm']
                )
    
    # Broadcast updated state
    broadcast_state()
    
    # Only publish to MQTT if this update did NOT originate from MQTT
    if not from_mqtt:
        publish_to_mqtt()


# Add this function to expose the websocket clients to other modules

def get_websocket_clients():
    """
    Get the current set of active WebSocket clients
    Returns:
        set: The set of active WebSocket clients
    """
    return websocket_clients

# Add this somewhere in the global scope
def reset_sensor_state():
    """Reset sensor state to a clean initial state"""
    global sensor_state
    sensor_state = {
        'spo2': None,
        'bpm': None,
        'perfusion': None,
        'status': None,
        'map_bp': None,
        'temp': None,
    }

# Add this new function to store event data
def store_event_data_for_alert(alert_id, data_points):
    """
    Store all cached event data for an alert (pulse ox or external alarm).
    Args:
        alert_id: ID of the alert
        data_points: List of data points to store
    """
    from crud import save_pulse_ox_data

    print(f"[state_manager] Storing {len(data_points)} data points for alert {alert_id}")

    for point in data_points:
        # If this is an external alarm event, extract sensor values from 'sensor_state'
        if 'sensor_state' in point:
            sensor = point['sensor_state']
            spo2 = sensor.get('spo2')
            bpm = sensor.get('bpm')
            perfusion = sensor.get('perfusion')
            status = sensor.get('status')
            motion = sensor.get('motion', "OFF")
            spo2_alarm = "OFF"
            hr_alarm = "OFF"
            raw_data = None
            timestamp = point.get('timestamp')
        else:
            # Pulse ox event format
            spo2 = point.get('spo2')
            bpm = point.get('bpm')
            perfusion = point.get('perfusion')
            status = point.get('status')
            motion = point.get('motion', "OFF")
            spo2_alarm = point.get('spo2_alarm', "OFF")
            hr_alarm = point.get('hr_alarm', "OFF")
            raw_data = point.get('raw_data', None)
            timestamp = point.get('timestamp')

        # Save to DB if not already saved
        if 'db_id' not in point:
            data_id = save_pulse_ox_data(
                spo2=spo2,
                bpm=bpm,
                pa=perfusion,
                status=status,
                motion=motion,
                spo2_alarm=spo2_alarm,
                hr_alarm=hr_alarm,
                raw_data=raw_data,
                timestamp=timestamp
            )
            point['db_id'] = data_id

    print(f"[state_manager] Successfully stored event data for alert {alert_id}")

# Add this function to broadcast alert updates

def broadcast_alert_updates():
    """
    Send alert update information to all connected WebSocket clients.
    This is called when alarms are triggered or cleared.
    """
    if not event_loop:
        print("[state_manager] Cannot broadcast alerts, event_loop not set.")
        return

    # Get counts of active alarms
    from crud import get_unacknowledged_alerts_count
    from crud import get_active_ventilator_alerts_count
    
    # Get the counts
    pulse_ox_alerts = get_unacknowledged_alerts_count()
    vent_alerts = get_active_ventilator_alerts_count()
    
    # Create the message to broadcast
    message = {
        "type": "alert_update",
        "alerts": {
            "pulse_ox": pulse_ox_alerts,
            "ventilator": vent_alerts
        }
    }
    
    # Send to all connected clients
    for ws in list(websocket_clients):
        try:
            asyncio.run_coroutine_threadsafe(ws.send_json(message), event_loop)
        except Exception as e:
            print(f"[state_manager] Failed to send alert update: {e}")
            websocket_clients.discard(ws)

def set_alarm_states(new_states):
    """
    Update alarm states and broadcast to websocket clients if changed.
    """
    global alarm_states
    changed = False
    for key in alarm_states:
        if alarm_states[key] != new_states.get(key, alarm_states[key]):
            changed = True
            break
    alarm_states = new_states.copy()
    if changed:
        # Broadcast immediately when alarm state changes
        broadcast_state()

def update_alarm_event_state():
    """
    Check alarm states and manage alert event lifecycle for external alarms.
    """
    global alarm_event_active, alarm_event_start_time, alarm_event_data_points, current_alert_id, event_data_points

    now = time.time()
    # If either alarm is active, start or continue the event
    if alarm_states.get("alarm1") or alarm_states.get("alarm2"):
        if not alarm_event_active:
            alarm_event_active = True
            alarm_event_start_time = now
            alarm_event_data_points = []
            print("[state_manager] External alarm event started.")
            # Start a new monitoring alert (or reuse your DB logic)
            current_alert_id = start_monitoring_alert(
                spo2=None,
                bpm=None,
                data_id=None,
                external_alarm_triggered=1
            )
        # Collect data points during the event
        alarm_event_data_points.append({
            "timestamp": datetime.now().isoformat(),
            "alarm1": alarm_states.get("alarm1"),
            "alarm2": alarm_states.get("alarm2"),
            "sensor_state": sensor_state.copy()
        })
    else:
        # If event was active, check if it's time to end it
        if alarm_event_active:
            if alarm_event_start_time is not None and (now - alarm_event_start_time) >= RECOVERY_SECONDS_REQUIRED:
                print("[state_manager] External alarm event ended after recovery period.")
                # Save event data to DB
                store_event_data_for_alert(current_alert_id, alarm_event_data_points)
                # End the alert in DB
                update_monitoring_alert(
                    alert_id=current_alert_id,
                    end_time=datetime.now().isoformat(),
                    external_alarm_triggered=0
                )
                # Reset event state
                alarm_event_active = False
                alarm_event_start_time = None
                alarm_event_data_points = []
                current_alert_id = None

def serialize_datetime_objects(obj):
    """
    Recursively convert datetime objects to ISO format strings in a dictionary/list structure.
    
    Args:
        obj: The object to serialize (dict, list, or primitive)
        
    Returns:
        The object with datetime objects converted to strings
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: serialize_datetime_objects(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [serialize_datetime_objects(item) for item in obj]
    else:
        return obj