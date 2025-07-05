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