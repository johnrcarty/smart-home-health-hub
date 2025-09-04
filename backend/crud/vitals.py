"""
Core vital signs and sensor data CRUD operations
"""
import logging
import pytz
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from models import BloodPressure, Temperature, Vital, PulseOxData

logger = logging.getLogger('crud')


# --- Blood Pressure CRUD ---
def save_blood_pressure(db: Session, systolic, diastolic, map_value=None, timestamp=None, notes=None):
    """
    Save blood pressure reading to database (Postgres)
    """
    now = datetime.now(timezone.utc)
    ts = timestamp or now
    
    # Ensure timestamp is timezone-aware
    if ts and hasattr(ts, 'tzinfo') and ts.tzinfo is None:
        eastern = pytz.timezone('US/Eastern')
        ts = eastern.localize(ts).astimezone(timezone.utc)
    elif isinstance(ts, str):
        try:
            ts = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        except:
            ts = now
    
    bp = BloodPressure(
        timestamp=ts,
        systolic=systolic,
        diastolic=diastolic,
        map=map_value,
        raw_data=notes,
        created_at=now
    )
    db.add(bp)
    db.commit()
    db.refresh(bp)
    logger.info(f"Blood pressure saved: {systolic}/{diastolic} (MAP: {map_value})")
    return bp.id


def get_latest_blood_pressure(db: Session):
    """Get the most recent blood pressure reading."""
    try:
        return db.query(BloodPressure).order_by(BloodPressure.timestamp.desc()).first()
    except Exception as e:
        logger.error(f"Error fetching latest blood pressure: {e}")
        return None


def get_blood_pressure_history(db: Session, limit=100):
    """
    Get blood pressure history

    Args:
        limit (int): Maximum number of records to return
    """
    try:
        return db.query(BloodPressure).order_by(BloodPressure.timestamp.desc()).limit(limit).all()
    except Exception as e:
        logger.error(f"Error fetching blood pressure history: {e}")
        return []


def get_last_n_blood_pressure(db: Session, n=5):
    """
    Get the last n blood pressure readings

    Args:
        n (int): Number of readings to retrieve

    Returns:
        list: List of dictionaries containing BP readings
    """
    try:
        results = db.query(BloodPressure).order_by(BloodPressure.timestamp.desc()).limit(n).all()

        # If we have no results, only add a single empty entry
        if len(results) == 0:
            return [{'datetime': '', 'systolic_bp': None, 'diastolic_bp': None, 'map_bp': None}]

        return [
            {
                'datetime': row.timestamp,
                'systolic_bp': row.systolic,
                'diastolic_bp': row.diastolic,
                'map_bp': row.map
            }
            for row in results
        ]
    except Exception as e:
        logger.error(f"Error fetching blood pressure history: {e}")
        # Return just one empty entry on error
        return [{'datetime': '', 'systolic_bp': None, 'diastolic_bp': None, 'map_bp': None}]


# --- Temperature CRUD ---
def save_temperature(db: Session, body_temp, skin_temp=None, timestamp=None, notes=None):
    """
    Save temperature reading to database (Postgres)
    """
    now = datetime.now(timezone.utc)
    ts = timestamp or now
    
    # Ensure timestamp is timezone-aware
    if ts and hasattr(ts, 'tzinfo') and ts.tzinfo is None:
        eastern = pytz.timezone('US/Eastern')
        ts = eastern.localize(ts).astimezone(timezone.utc)
    elif isinstance(ts, str):
        try:
            ts = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        except:
            ts = now
    
    temp = Temperature(
        timestamp=ts,
        skin_temp=skin_temp,
        body_temp=body_temp,
        raw_data=notes,
        created_at=now
    )
    db.add(temp)
    db.commit()
    db.refresh(temp)
    logger.info(f"Temperature saved: Skin: {skin_temp}°, Body: {body_temp}°")
    return temp.id


def get_last_n_temperature(db: Session, n=5):
    """
    Get the last n temperature readings

    Args:
        n (int): Number of readings to retrieve

    Returns:
        list: List of dictionaries containing temperature readings
    """
    try:
        results = db.query(Temperature).order_by(Temperature.timestamp.desc()).limit(n).all()

        # If we have no results, only add a single empty entry
        if len(results) == 0:
            return [{'datetime': '', 'skin_temp': None, 'body_temp': None}]

        return [
            {
                'datetime': row.timestamp,
                'skin_temp': row.skin_temp,
                'body_temp': row.body_temp
            }
            for row in results
        ]
    except Exception as e:
        logger.error(f"Error fetching temperature history: {e}")
        # Return just one empty entry on error
        return [{'datetime': '', 'skin_temp': None, 'body_temp': None}]


# --- Generic Vital CRUD ---
def save_vital(db: Session, vital_type, value, timestamp=None, notes=None, vital_group=None):
    """
    Save a generic vital reading to database (Postgres)
    """
    now = datetime.now(timezone.utc)
    ts = timestamp or now
    
    # Ensure timestamp is timezone-aware (convert to UTC if naive)
    if ts and hasattr(ts, 'tzinfo') and ts.tzinfo is None:
        # Assume naive datetime is in local timezone and convert to UTC
        eastern = pytz.timezone('US/Eastern')
        ts = eastern.localize(ts).astimezone(timezone.utc)
    elif isinstance(ts, str):
        # Parse string timestamp and ensure it's UTC
        try:
            ts = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        except:
            ts = now
    
    vital = Vital(
        timestamp=ts,
        vital_type=vital_type,
        value=value,
        notes=notes,
        vital_group=vital_group,
        created_at=now
    )
    db.add(vital)
    db.commit()
    db.refresh(vital)
    logger.info(f"Vital saved: {vital_type}={value}, group={vital_group}")
    return vital.id


def get_distinct_vital_types(db: Session):
    logger.info(f"DB connection: {db.bind.url}")
    logger.info("Fetching distinct vital types...")
    types = db.query(Vital.vital_type).filter(Vital.vital_type.isnot(None)).filter(Vital.vital_type != '').distinct().all()
    logger.info(f"Distinct vital types fetched: {types}")
    return [t[0] for t in types]


def get_vitals_by_type_paginated(db: Session, vital_type, page=1, page_size=20):
    """
    Get paginated history of a specific vital type
    """
    query = db.query(Vital).filter(Vital.vital_type == vital_type)
    total = query.count()
    records = query.order_by(Vital.timestamp.desc()).offset((page-1)*page_size).limit(page_size).all()
    total_pages = (total + page_size - 1) // page_size
    return {
        'records': [
            {
                'datetime': v.timestamp,
                'value': v.value,
                'notes': v.notes,
                'vital_group': v.vital_group
            } for v in records
        ],
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': total_pages
    }


def get_vitals_by_type(db: Session, vital_type, limit=100):
    """
    Get history of a specific vital type

    Args:
        vital_type (str): Type of vital (weight, calories, water, etc.)
        limit (int): Maximum number of records to return

    Returns:
        list: List of dictionaries containing readings
    """
    try:
        results = db.query(Vital).filter(Vital.vital_type == vital_type).order_by(Vital.timestamp.desc()).limit(limit).all()

        return [
            {
                'datetime': row.timestamp,
                'value': row.value,
                'notes': row.notes,
                'vital_group': row.vital_group
            }
            for row in results
        ]
    except Exception as e:
        logger.error(f"Error fetching {vital_type} history: {e}")
        return []


# --- Pulse Oximeter CRUD ---
def save_pulse_ox_data(db: Session, spo2, bpm, pa, status=None, motion=None, spo2_alarm=None, hr_alarm=None, raw_data=None, timestamp=None):
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
        timestamp (str): Optional ISO timestamp, defaults to now if not provided

    Returns:
        int: ID of the inserted record or None on error
    """
    try:
        now = datetime.now().isoformat()
        ts = timestamp or now  # Use provided timestamp or current time

        pulse_ox = PulseOxData(
            timestamp=ts,
            spo2=spo2,
            bpm=bpm,
            pa=pa,
            status=status,
            motion=motion,
            spo2_alarm=spo2_alarm,
            hr_alarm=hr_alarm,
            raw_data=raw_data,
            created_at=now
        )

        db.add(pulse_ox)
        db.commit()
        db.refresh(pulse_ox)
        logger.info(f"Pulse ox data saved: SpO2: {spo2}%, BPM: {bpm}, PA: {pa}")
        return pulse_ox.id
    except Exception as e:
        logger.error(f"Error saving pulse ox data: {e}")
        return None


def save_pulse_ox_batch(db: Session, data_points):
    """
    Save a batch of pulse oximeter readings to database

    Args:
        db (Session): Database session
        data_points (list): List of pulse ox data dictionaries

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        now = datetime.now().isoformat()
        
        for data_point in data_points:
            pulse_ox = PulseOxData(
                timestamp=data_point.get('timestamp', now),
                spo2=data_point.get('spo2'),
                bpm=data_point.get('bpm'),
                pa=data_point.get('pa'),
                status=data_point.get('status'),
                motion=data_point.get('motion'),
                spo2_alarm=data_point.get('spo2_alarm'),
                hr_alarm=data_point.get('hr_alarm'),
                raw_data=data_point.get('raw_data'),
                created_at=now
            )
            db.add(pulse_ox)
        
        db.commit()
        logger.info(f"Batch saved {len(data_points)} pulse ox readings")
        return True
    except Exception as e:
        logger.error(f"Error saving pulse ox batch: {e}")
        db.rollback()
        return False


def get_pulse_ox_data_by_date(db: Session, date_str):
    """
    Get all pulse ox data for a specific date

    Args:
        db (Session): Database session
        date_str (str): Date string in YYYY-MM-DD format

    Returns:
        list: List of pulse ox readings for the date
    """
    try:
        # Parse the date and create start/end datetime objects
        from datetime import datetime, time
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        start_datetime = datetime.combine(date_obj, time.min)
        end_datetime = datetime.combine(date_obj, time.max)
        
        data = db.query(PulseOxData).filter(
            PulseOxData.timestamp >= start_datetime,
            PulseOxData.timestamp <= end_datetime
        ).order_by(PulseOxData.timestamp.asc()).all()
        
        return data
    except Exception as e:
        logger.error(f"Error getting pulse ox data for date {date_str}: {e}")
        return []


def analyze_pulse_ox_day(db: Session, date_str):
    """
    Analyze pulse ox data for a specific day and return SpO2 distribution

    Args:
        db (Session): Database session
        date_str (str): Date string in YYYY-MM-DD format

    Returns:
        dict: Analysis results including time logged, SpO2 distribution, etc.
    """
    try:
        data = get_pulse_ox_data_by_date(db, date_str)
        
        if not data:
            return {
                'date': date_str,
                'total_readings': 0,
                'time_logged_minutes': 0,
                'spo2_distribution': {}
            }
        
        # Filter out None values and 0 values for SpO2 (0 indicates sensor error)
        valid_spo2_readings = [reading for reading in data if reading.spo2 is not None and reading.spo2 > 0]
        valid_bpm_readings = [reading for reading in data if reading.bpm is not None and reading.bpm > 0]
        
        # Count zero/error readings for reporting
        zero_spo2_readings = [reading for reading in data if reading.spo2 is not None and reading.spo2 == 0]
        zero_bpm_readings = [reading for reading in data if reading.bpm is not None and reading.bpm == 0]
        
        # Calculate time logged (assume readings every ~5 seconds, so multiply by 5 and convert to minutes)
        time_logged_minutes = (len(data) * 5) / 60
        
        # Categorize SpO2 readings - Full breakdown
        spo2_distribution = {
            'high_90s_97_plus': 0,
            'mid_90s_94_96': 0,
            'low_90s_90_93': 0,
            'high_eighties_85_89': 0,
            'low_eighties_80_84': 0,
            'seventies_70_79': 0,
            'sixties_60_69': 0,
            'fifties_50_59': 0,
            'forties_40_49': 0,
            'thirties_30_39': 0,
            'twenties_20_29': 0,
            'below_twenty': 0,
            'zero_errors': 0
        }
        
        for reading in valid_spo2_readings:
            spo2 = reading.spo2
            if spo2 >= 97:
                spo2_distribution['high_90s_97_plus'] += 1
            elif spo2 >= 94:
                spo2_distribution['mid_90s_94_96'] += 1
            elif spo2 >= 90:
                spo2_distribution['low_90s_90_93'] += 1
            elif spo2 >= 85:
                spo2_distribution['high_eighties_85_89'] += 1
            elif spo2 >= 80:
                spo2_distribution['low_eighties_80_84'] += 1
            elif spo2 >= 70:
                spo2_distribution['seventies_70_79'] += 1
            elif spo2 >= 60:
                spo2_distribution['sixties_60_69'] += 1
            elif spo2 >= 50:
                spo2_distribution['fifties_50_59'] += 1
            elif spo2 >= 40:
                spo2_distribution['forties_40_49'] += 1
            elif spo2 >= 30:
                spo2_distribution['thirties_30_39'] += 1
            elif spo2 >= 20:
                spo2_distribution['twenties_20_29'] += 1
            else:
                spo2_distribution['below_twenty'] += 1
        
        # Count zero/error readings separately
        spo2_distribution['zero_errors'] = len(zero_spo2_readings)
        
        # Convert counts to percentages
        total_all_readings = len(valid_spo2_readings) + len(zero_spo2_readings)
        if total_all_readings > 0:
            for key in spo2_distribution:
                spo2_distribution[key] = round((spo2_distribution[key] / total_all_readings) * 100, 1)
        
        # Calculate basic statistics (excluding zero/error readings for averages)
        spo2_values = [r.spo2 for r in valid_spo2_readings]
        bpm_values = [r.bpm for r in valid_bpm_readings]
        
        result = {
            'date': date_str,
            'total_readings': len(data),
            'valid_spo2_readings': len(valid_spo2_readings),
            'valid_bpm_readings': len(valid_bpm_readings),
            'error_spo2_readings': len(zero_spo2_readings),
            'error_bpm_readings': len(zero_bpm_readings),
            'time_logged_minutes': round(time_logged_minutes, 1) if time_logged_minutes else 0,
            'time_logged_hours': round(time_logged_minutes / 60, 2) if time_logged_minutes else 0,
            'spo2_distribution': spo2_distribution,
            'avg_spo2': round(sum(spo2_values) / len(spo2_values), 1) if spo2_values else None,
            'min_spo2': min(spo2_values) if spo2_values else None,
            'max_spo2': max(spo2_values) if spo2_values else None,
            'avg_bpm': round(sum(bpm_values) / len(bpm_values), 1) if bpm_values else None,
            'min_bpm': min(bpm_values) if bpm_values else None,
            'max_bpm': max(bpm_values) if bpm_values else None
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing pulse ox data for date {date_str}: {e}")
        return {
            'date': date_str,
            'error': str(e),
            'total_readings': 0,
            'time_logged_minutes': 0,
            'spo2_distribution': {}
        }


def get_available_pulse_ox_dates(db: Session, limit=30):
    """
    Get list of dates that have pulse ox data

    Args:
        db (Session): Database session
        limit (int): Maximum number of dates to return

    Returns:
        list: List of dates that have pulse ox data
    """
    try:
        from sqlalchemy import func, distinct
        
        # Get distinct dates from pulse ox data
        dates = db.query(
            func.date(PulseOxData.timestamp).label('date')
        ).distinct().order_by(
            func.date(PulseOxData.timestamp).desc()
        ).limit(limit).all()
        
        return [date.date.strftime('%Y-%m-%d') for date in dates]
        
    except Exception as e:
        logger.error(f"Error getting available pulse ox dates: {e}")
        return []
