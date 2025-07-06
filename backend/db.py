import sqlite3
import os
import json
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('db')

# Database configuration
DB_PATH = os.getenv('DB_PATH', 'sensor_data.db')

def init_db():
    """Initialize the database with required tables."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create blood pressure table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS blood_pressure (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            systolic INTEGER NOT NULL,
            diastolic INTEGER NOT NULL,
            map INTEGER NOT NULL,
            raw_data TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        ''')
        
        # Create temperature table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS temperature (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            skin_temp REAL,
            body_temp REAL,
            raw_data TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        ''')
        
        # Create generic vitals table for other measurements
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS vitals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            vital_type TEXT NOT NULL,
            value REAL NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL
        )
        ''')
        
        # Create settings table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            data_type TEXT NOT NULL,
            description TEXT,
            updated_at TEXT NOT NULL
        )
        ''')
        
        # Create pulse ox continuous data log
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS pulse_ox_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            spo2 INTEGER,
            bpm INTEGER,
            pa REAL,
            status TEXT,
            motion TEXT,
            spo2_alarm TEXT,
            hr_alarm TEXT,
            raw_data TEXT,
            created_at TEXT NOT NULL
        )
        ''')
        
        # Create monitoring alerts table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS monitoring_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time TEXT NOT NULL,
            end_time TEXT,
            start_data_id INTEGER,
            end_data_id INTEGER,
            acknowledged INTEGER DEFAULT 0,
            
            -- Pulse Ox Metrics
            spo2_min INTEGER,
            bpm_min INTEGER,
            spo2_max INTEGER,
            bpm_max INTEGER,
            spo2_alarm_triggered INTEGER DEFAULT 0,
            hr_alarm_triggered INTEGER DEFAULT 0,
            
            -- External Alarm Line
            external_alarm_triggered INTEGER DEFAULT 0,
            
            -- Oxygen Usage
            oxygen_used INTEGER DEFAULT 0,      -- 0 = No, 1 = Yes
            oxygen_highest FLOAT,               -- Max liters or percent
            oxygen_unit TEXT,                   -- Example: "L/min" or "%"
            
            created_at TEXT NOT NULL
        )
        ''')
        
        conn.commit()
        logger.info(f"Database initialized at {DB_PATH}")
    except sqlite3.Error as e:
        logger.error(f"Database initialization error: {e}")
    finally:
        if conn:
            conn.close()

def save_blood_pressure(systolic, diastolic, map_value, raw_data):
    """
    Save blood pressure reading to database
    
    Args:
        systolic (int): Systolic pressure value
        diastolic (int): Diastolic pressure value
        map_value (int): Mean Arterial Pressure value
        raw_data (str): Raw data string received from sensor
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        cursor.execute(
            '''
            INSERT INTO blood_pressure 
            (timestamp, systolic, diastolic, map, raw_data, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (now, systolic, diastolic, map_value, raw_data, now)
        )
        
        conn.commit()
        logger.info(f"Blood pressure saved: {systolic}/{diastolic} (MAP: {map_value})")
        return cursor.lastrowid
    except sqlite3.Error as e:
        logger.error(f"Error saving blood pressure: {e}")
        return None
    finally:
        if conn:
            conn.close()

def save_temperature(skin_temp, body_temp, raw_data):
    """
    Save temperature reading to database
    
    Args:
        skin_temp (float): Skin temperature value
        body_temp (float): Body temperature value
        raw_data (str): Raw data string received from sensor
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        cursor.execute(
            '''
            INSERT INTO temperature 
            (timestamp, skin_temp, body_temp, raw_data, created_at)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (now, skin_temp, body_temp, raw_data, now)
        )
        
        conn.commit()
        logger.info(f"Temperature saved: Skin: {skin_temp}°, Body: {body_temp}°")
        return cursor.lastrowid
    except sqlite3.Error as e:
        logger.error(f"Error saving temperature: {e}")
        return None
    finally:
        if conn:
            conn.close()

def save_vital(vital_type, value, timestamp=None, notes=None):
    """
    Save a generic vital reading to database
    
    Args:
        vital_type (str): Type of vital (weight, calories, water, etc.)
        value (float or int): Value of the vital
        timestamp (str, optional): Timestamp for the reading. Defaults to current time.
        notes (str, optional): Additional notes.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        timestamp = timestamp or now
        
        cursor.execute(
            '''
            INSERT INTO vitals 
            (timestamp, vital_type, value, notes, created_at)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (timestamp, vital_type, value, notes, now)
        )
        
        conn.commit()
        logger.info(f"Vital saved: {vital_type}={value}")
        return cursor.lastrowid
    except sqlite3.Error as e:
        logger.error(f"Error saving vital: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_latest_blood_pressure():
    """Get the most recent blood pressure reading."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            '''
            SELECT timestamp, systolic, diastolic, map 
            FROM blood_pressure 
            ORDER BY timestamp DESC 
            LIMIT 1
            '''
        )
        
        result = cursor.fetchone()
        if result:
            return {
                'timestamp': result[0],
                'systolic': result[1],
                'diastolic': result[2],
                'map': result[3]
            }
        return None
    except sqlite3.Error as e:
        logger.error(f"Error fetching latest blood pressure: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_blood_pressure_history(limit=100):
    """
    Get blood pressure history
    
    Args:
        limit (int): Maximum number of records to return
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        cursor = conn.cursor()
        
        cursor.execute(
            '''
            SELECT timestamp, systolic, diastolic, map 
            FROM blood_pressure 
            ORDER BY timestamp DESC 
            LIMIT ?
            ''', 
            (limit,)
        )
        
        results = cursor.fetchall()
        return [dict(row) for row in results]
    except sqlite3.Error as e:
        logger.error(f"Error fetching blood pressure history: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_last_n_blood_pressure(n=5):
    """
    Get the last n blood pressure readings
    
    Args:
        n (int): Number of readings to retrieve
    
    Returns:
        list: List of dictionaries containing BP readings
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        cursor = conn.cursor()
        
        cursor.execute(
            '''
            SELECT timestamp, systolic, diastolic, map 
            FROM blood_pressure 
            ORDER BY timestamp DESC 
            LIMIT ?
            ''', 
            (n,)
        )
        
        results = cursor.fetchall()
        bp_data = [
            {
                'datetime': row['timestamp'],
                'systolic_bp': row['systolic'], 
                'diastolic_bp': row['diastolic'], 
                'map_bp': row['map']
            } 
            for row in results
        ]
        
        # If we have no results, only add a single empty entry
        if len(bp_data) == 0:
            return [{'datetime': '', 'systolic_bp': None, 'diastolic_bp': None, 'map_bp': None}]
            
        return bp_data
    except sqlite3.Error as e:
        logger.error(f"Error fetching blood pressure history: {e}")
        # Return just one empty entry on error
        return [{'datetime': '', 'systolic_bp': None, 'diastolic_bp': None, 'map_bp': None}]
    finally:
        if conn:
            conn.close()

def get_last_n_temperature(n=5):
    """
    Get the last n temperature readings
    
    Args:
        n (int): Number of readings to retrieve
    
    Returns:
        list: List of dictionaries containing temperature readings
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        cursor = conn.cursor()
        
        cursor.execute(
            '''
            SELECT timestamp, skin_temp, body_temp 
            FROM temperature 
            ORDER BY timestamp DESC 
            LIMIT ?
            ''', 
            (n,)
        )
        
        results = cursor.fetchall()
        temp_data = [
            {
                'datetime': row['timestamp'],
                'skin_temp': row['skin_temp'], 
                'body_temp': row['body_temp']
            } 
            for row in results
        ]
        
        # If we have no results, only add a single empty entry
        if len(temp_data) == 0:
            return [{'datetime': '', 'skin_temp': None, 'body_temp': None}]
            
        return temp_data
    except sqlite3.Error as e:
        logger.error(f"Error fetching temperature history: {e}")
        # Return just one empty entry on error
        return [{'datetime': '', 'skin_temp': None, 'body_temp': None}]
    finally:
        if conn:
            conn.close()

def get_vitals_by_type(vital_type, limit=100):
    """
    Get history of a specific vital type
    
    Args:
        vital_type (str): Type of vital (weight, calories, water, etc.)
        limit (int): Maximum number of records to return
    
    Returns:
        list: List of dictionaries containing readings
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        cursor = conn.cursor()
        
        cursor.execute(
            '''
            SELECT timestamp, value, notes 
            FROM vitals
            WHERE vital_type = ?
            ORDER BY timestamp DESC 
            LIMIT ?
            ''', 
            (vital_type, limit)
        )
        
        results = cursor.fetchall()
        vitals_data = [
            {
                'datetime': row['timestamp'],
                'value': row['value'],
                'notes': row['notes']
            } 
            for row in results
        ]
        
        return vitals_data
    except sqlite3.Error as e:
        logger.error(f"Error fetching {vital_type} history: {e}")
        return []
    finally:
        if conn:
            conn.close()

def save_setting(key, value, data_type="string", description=None):
    """
    Save a setting to the database
    
    Args:
        key (str): Setting key/name
        value (any): Setting value (will be converted to string)
        data_type (str): Data type (string, int, float, bool, json)
        description (str, optional): Description of the setting
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        # Convert value to string for storage
        str_value = str(value)
        
        # Check if setting exists
        cursor.execute("SELECT key FROM settings WHERE key = ?", (key,))
        exists = cursor.fetchone() is not None
        
        if exists:
            cursor.execute(
                '''
                UPDATE settings 
                SET value = ?, data_type = ?, description = ?, updated_at = ?
                WHERE key = ?
                ''',
                (str_value, data_type, description, now, key)
            )
        else:
            cursor.execute(
                '''
                INSERT INTO settings 
                (key, value, data_type, description, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ''',
                (key, str_value, data_type, description, now)
            )
        
        conn.commit()
        logger.info(f"Setting saved: {key}={value}")
        return True
    except sqlite3.Error as e:
        logger.error(f"Error saving setting: {e}")
        return False
    finally:
        if conn:
            conn.close()

def get_setting(key, default=None):
    """
    Get a setting from the database with proper type conversion
    
    Args:
        key (str): Setting key/name
        default (any, optional): Default value if setting not found
    
    Returns:
        any: The setting value with proper type conversion
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT value, data_type FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        
        if not row:
            return default
        
        value = row['value']
        data_type = row['data_type']
        
        # Convert to appropriate type
        if data_type == 'int':
            return int(value)
        elif data_type == 'float':
            return float(value)
        elif data_type == 'bool':
            return value.lower() in ('true', '1', 'yes', 'y')
        elif data_type == 'json':
            return json.loads(value)
        else:  # string or anything else
            return value
            
    except sqlite3.Error as e:
        logger.error(f"Error fetching setting {key}: {e}")
        return default
    finally:
        if conn:
            conn.close()

def get_all_settings():
    """
    Get all settings from the database
    
    Returns:
        dict: Dictionary of all settings with proper type conversion
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT key, value, data_type, description, updated_at FROM settings")
        rows = cursor.fetchall()
        
        settings = {}
        for row in rows:
            key = row['key']
            value = row['value']
            data_type = row['data_type']
            
            # Convert to appropriate type
            if data_type == 'int':
                converted_value = int(value)
            elif data_type == 'float':
                converted_value = float(value)
            elif data_type == 'bool':
                converted_value = value.lower() in ('true', '1', 'yes', 'y')
            elif data_type == 'json':
                converted_value = json.loads(value)
            else:  # string or anything else
                converted_value = value
            
            settings[key] = {
                'value': converted_value,
                'type': data_type,
                'description': row['description'],
                'updated_at': row['updated_at']
            }
            
        return settings
            
    except sqlite3.Error as e:
        logger.error(f"Error fetching all settings: {e}")
        return {}
    finally:
        if conn:
            conn.close()

def delete_setting(key):
    """
    Delete a setting from the database
    
    Args:
        key (str): Setting key/name
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM settings WHERE key = ?", (key,))
        conn.commit()
        
        deleted = cursor.rowcount > 0
        if deleted:
            logger.info(f"Setting deleted: {key}")
        else:
            logger.info(f"Setting not found for deletion: {key}")
        
        return deleted
    except sqlite3.Error as e:
        logger.error(f"Error deleting setting {key}: {e}")
        return False
    finally:
        if conn:
            conn.close()

def save_pulse_ox_data(spo2, bpm, pa, status=None, motion=None, spo2_alarm=None, hr_alarm=None, raw_data=None):
    """
    Save pulse oximeter reading to database
    
    Args:
        spo2 (int): Blood oxygen level
        bpm (int): Pulse rate
        pa (float): Perfusion index
        status (str): Device status
        motion (str): Motion detection ("ON" or "OFF")
        spo2_alarm (str): SpO2 alarm status ("ON" or "OFF")
        hr_alarm (str): Heart rate alarm status ("ON" or "OFF")
        raw_data (str): Raw data string received from sensor
    
    Returns:
        int: ID of the inserted record or None on error
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        cursor.execute(
            '''
            INSERT INTO pulse_ox_data
            (timestamp, spo2, bpm, pa, status, motion, spo2_alarm, hr_alarm, raw_data, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (now, spo2, bpm, pa, status, motion, spo2_alarm, hr_alarm, raw_data, now)
        )
        
        conn.commit()
        record_id = cursor.lastrowid
        logger.info(f"Pulse ox data saved: SpO2: {spo2}%, BPM: {bpm}, PA: {pa}")
        return record_id
    except sqlite3.Error as e:
        logger.error(f"Error saving pulse ox data: {e}")
        return None
    finally:
        if conn:
            conn.close()

def start_monitoring_alert(spo2=None, bpm=None, data_id=None, spo2_alarm_triggered=0, hr_alarm_triggered=0):
    """
    Start a new monitoring alert event
    
    Args:
        spo2 (int): Initial SpO2 reading
        bpm (int): Initial BPM reading
        data_id (int): ID of the pulse_ox_data record
        spo2_alarm_triggered (int): Whether SpO2 alarm was triggered
        hr_alarm_triggered (int): Whether heart rate alarm was triggered
        
    Returns:
        int: ID of the inserted alert or None on error
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        cursor.execute(
            '''
            INSERT INTO monitoring_alerts
            (start_time, start_data_id, spo2_min, spo2_max, bpm_min, bpm_max, 
             spo2_alarm_triggered, hr_alarm_triggered, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (now, data_id, spo2, spo2, bpm, bpm, spo2_alarm_triggered, hr_alarm_triggered, now)
        )
        
        conn.commit()
        alert_id = cursor.lastrowid
        logger.info(f"Started monitoring alert #{alert_id} - SpO2: {spo2}%, BPM: {bpm}")
        return alert_id
    except sqlite3.Error as e:
        logger.error(f"Error starting monitoring alert: {e}")
        return None
    finally:
        if conn:
            conn.close()

def update_monitoring_alert(alert_id, end_time=None, end_data_id=None, spo2=None, bpm=None, 
                           spo2_alarm_triggered=None, hr_alarm_triggered=None,
                           external_alarm_triggered=None, oxygen_used=None,
                           oxygen_highest=None, oxygen_unit=None):
    """
    Update an existing monitoring alert
    
    Args:
        alert_id (int): ID of the alert to update
        end_time (str): End time if alert is completed
        end_data_id (int): ID of the final pulse_ox_data record
        spo2 (int): Current SpO2 reading to update min/max
        bpm (int): Current BPM reading to update min/max
        spo2_alarm_triggered (int): Whether SpO2 alarm was triggered
        hr_alarm_triggered (int): Whether heart rate alarm was triggered
        external_alarm_triggered (int): Whether external alarm was triggered
        oxygen_used (int): Whether oxygen was used
        oxygen_highest (float): Highest oxygen level used
        oxygen_unit (str): Unit of oxygen measurement
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # First, get current values
        cursor.execute('SELECT spo2_min, spo2_max, bpm_min, bpm_max FROM monitoring_alerts WHERE id = ?', (alert_id,))
        result = cursor.fetchone()
        
        if not result:
            logger.error(f"Alert ID {alert_id} not found for update")
            return False
            
        current_spo2_min, current_spo2_max, current_bpm_min, current_bpm_max = result
        
        # Calculate new min/max values
        if spo2 is not None:
            if current_spo2_min is None or spo2 < current_spo2_min:
                current_spo2_min = spo2
            if current_spo2_max is None or spo2 > current_spo2_max:
                current_spo2_max = spo2
                
        if bpm is not None:
            if current_bpm_min is None or bpm < current_bpm_min:
                current_bpm_min = bpm
            if current_bpm_max is None or bpm > current_bpm_max:
                current_bpm_max = bpm
        
        # Build update query dynamically
        update_fields = []
        params = []
        
        if end_time:
            update_fields.append("end_time = ?")
            params.append(end_time)
        
        if end_data_id:
            update_fields.append("end_data_id = ?")
            params.append(end_data_id)
        
        if spo2 is not None:
            update_fields.append("spo2_min = ?")
            params.append(current_spo2_min)
            update_fields.append("spo2_max = ?")
            params.append(current_spo2_max)
        
        if bpm is not None:
            update_fields.append("bpm_min = ?")
            params.append(current_bpm_min)
            update_fields.append("bpm_max = ?")
            params.append(current_bpm_max)
        
        if spo2_alarm_triggered is not None:
            update_fields.append("spo2_alarm_triggered = ?")
            params.append(spo2_alarm_triggered)
        
        if hr_alarm_triggered is not None:
            update_fields.append("hr_alarm_triggered = ?")
            params.append(hr_alarm_triggered)
        
        if external_alarm_triggered is not None:
            update_fields.append("external_alarm_triggered = ?")
            params.append(external_alarm_triggered)
        
        if oxygen_used is not None:
            update_fields.append("oxygen_used = ?")
            params.append(oxygen_used)
        
        if oxygen_highest is not None:
            update_fields.append("oxygen_highest = ?")
            params.append(oxygen_highest)
        
        if oxygen_unit is not None:
            update_fields.append("oxygen_unit = ?")
            params.append(oxygen_unit)
        
        if not update_fields:
            logger.warning("No fields to update for alert")
            return True
        
        query = f"UPDATE monitoring_alerts SET {', '.join(update_fields)} WHERE id = ?"
        params.append(alert_id)
        
        cursor.execute(query, params)
        conn.commit()
        
        logger.info(f"Updated monitoring alert #{alert_id}")
        return True
    except sqlite3.Error as e:
        logger.error(f"Error updating monitoring alert: {e}")
        return False
    finally:
        if conn:
            conn.close()

def acknowledge_alert(alert_id):
    """
    Mark an alert as acknowledged
    
    Args:
        alert_id (int): ID of the alert to acknowledge
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('UPDATE monitoring_alerts SET acknowledged = 1 WHERE id = ?', (alert_id,))
        conn.commit()
        
        success = cursor.rowcount > 0
        if success:
            logger.info(f"Alert #{alert_id} acknowledged")
        else:
            logger.warning(f"Alert #{alert_id} not found for acknowledgment")
        
        return success
    except sqlite3.Error as e:
        logger.error(f"Error acknowledging alert: {e}")
        return False
    finally:
        if conn:
            conn.close()

def get_unacknowledged_alerts_count():
    """
    Get count of unacknowledged alerts
    
    Returns:
        int: Number of unacknowledged alerts
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM monitoring_alerts WHERE acknowledged = 0')
        count = cursor.fetchone()[0]
        
        return count
    except sqlite3.Error as e:
        logger.error(f"Error getting unacknowledged alert count: {e}")
        return 0
    finally:
        if conn:
            conn.close()

def get_monitoring_alerts(limit=50, include_acknowledged=False, detailed=False):
    """
    Get monitoring alert history
    
    Args:
        limit (int): Maximum number of alerts to return
        include_acknowledged (bool): Whether to include acknowledged alerts
        detailed (bool): Whether to include detailed pulse ox data
        
    Returns:
        list: List of alert records
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = '''
        SELECT * FROM monitoring_alerts 
        '''
        
        if not include_acknowledged:
            query += 'WHERE acknowledged = 0 '
            
        query += 'ORDER BY start_time DESC LIMIT ?'
        
        cursor.execute(query, (limit,))
        
        results = cursor.fetchall()
        alerts = []
        
        for row in results:
            alert = dict(row)
            
            if detailed and row['start_data_id']:
                # Get all pulse ox data between start and end
                data_query = '''
                SELECT * FROM pulse_ox_data 
                WHERE id >= ? AND (? IS NULL OR id <= ?)
                ORDER BY timestamp ASC
                '''
                
                data_cursor = conn.cursor()
                data_cursor.execute(data_query, 
                                   (row['start_data_id'], 
                                    row['end_data_id'] is not None, 
                                    row['end_data_id'] or 0))
                
                data_results = data_cursor.fetchall()
                alert['data_points'] = [dict(data_row) for data_row in data_results]
            
            alerts.append(alert)
        
        return alerts
    except sqlite3.Error as e:
        logger.error(f"Error fetching monitoring alerts: {e}")
        return []
    finally:
        if conn:
            conn.close()