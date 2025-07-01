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
        
        # Add any other tables you might need here
        
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