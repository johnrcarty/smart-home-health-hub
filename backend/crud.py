import logging
from datetime import datetime
import json
from .db import get_db_connection

logger = logging.getLogger('crud')

# --- Blood Pressure CRUD ---
def save_blood_pressure(systolic, diastolic, map_value, raw_data):
    """
    Save blood pressure reading to database (Postgres)
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute(
            '''
            INSERT INTO blood_pressure 
            (timestamp, systolic, diastolic, map, raw_data, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            ''',
            (now, systolic, diastolic, map_value, raw_data, now)
        )
        bp_id = cursor.fetchone()[0]
        conn.commit()
        logger.info(f"Blood pressure saved: {systolic}/{diastolic} (MAP: {map_value})")
        return bp_id
    except Exception as e:
        logger.error(f"Error saving blood pressure: {e}")
        return None
    finally:
        if conn:
            conn.close()

# --- Temperature CRUD ---
def save_temperature(skin_temp, body_temp, raw_data):
    """
    Save temperature reading to database (Postgres)
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute(
            '''
            INSERT INTO temperature 
            (timestamp, skin_temp, body_temp, raw_data, created_at)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            ''',
            (now, skin_temp, body_temp, raw_data, now)
        )
        temp_id = cursor.fetchone()[0]
        conn.commit()
        logger.info(f"Temperature saved: Skin: {skin_temp}°, Body: {body_temp}°")
        return temp_id
    except Exception as e:
        logger.error(f"Error saving temperature: {e}")
        return None
    finally:
        if conn:
            conn.close()

# --- Generic Vital CRUD ---
def save_vital(vital_type, value, timestamp=None, notes=None):
    """
    Save a generic vital reading to database (Postgres)
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        timestamp = timestamp or now
        cursor.execute(
            '''
            INSERT INTO vitals 
            (timestamp, vital_type, value, notes, created_at)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            ''',
            (timestamp, vital_type, value, notes, now)
        )
        vital_id = cursor.fetchone()[0]
        conn.commit()
        logger.info(f"Vital saved: {vital_type}={value}")
        return vital_id
    except Exception as e:
        logger.error(f"Error saving vital: {e}")
        return None
    finally:
        if conn:
            conn.close()

# --- Get Distinct Vital Types ---
def get_distinct_vital_types():
    """
    Get a distinct list of vital_type values from the vitals table
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT vital_type FROM vitals')
        types = [row['vital_type'] for row in cursor.fetchall()]
        return types
    except Exception as e:
        logger.error(f"Error fetching distinct vital types: {e}")
        return []
    finally:
        if conn:
            conn.close()

# --- Paginated Vital History ---
def get_vitals_by_type_paginated(vital_type, page=1, page_size=20):
    """
    Get paginated history of a specific vital type
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        offset = (page - 1) * page_size
        cursor.execute(
            '''
            SELECT timestamp, value, notes 
            FROM vitals 
            WHERE vital_type = %s 
            ORDER BY timestamp DESC 
            LIMIT %s OFFSET %s
            ''',
            (vital_type, page_size, offset)
        )
        records = cursor.fetchall()
        cursor.execute(
            'SELECT COUNT(*) FROM vitals WHERE vital_type = %s',
            (vital_type,)
        )
        total = cursor.fetchone()['count']
        total_pages = (total + page_size - 1) // page_size
        return {
            'records': records,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages
        }
    except Exception as e:
        logger.error(f"Error fetching paginated vital history: {e}")
        return {'records': [], 'total': 0, 'page': page, 'page_size': page_size, 'total_pages': 1}
    finally:
        if conn:
            conn.close()

# Add other CRUD functions as needed, following the same pattern.
