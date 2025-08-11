import logging
import json
from datetime import datetime, timedelta
from croniter import croniter
from sqlalchemy.orm import Session
from db import get_db
from models import (BloodPressure, Temperature, Vital, Setting, PulseOxData,
    MonitoringAlert, Equipment, EquipmentChangeLog, VentilatorAlert, ExternalAlarm, 
    Medication, MedicationSchedule, MedicationLog, CareTask, CareTaskSchedule, CareTaskLog, CareTaskCategory)

logger = logging.getLogger('crud')

# --- Blood Pressure CRUD ---
def save_blood_pressure(db: Session, systolic, diastolic, map_value, raw_data):
    """
    Save blood pressure reading to database (Postgres)
    """
    now = datetime.now()
    bp = BloodPressure(
        timestamp=now,
        systolic=systolic,
        diastolic=diastolic,
        map=map_value,
        raw_data=raw_data,
        created_at=now
    )
    db.add(bp)
    db.commit()
    db.refresh(bp)
    logger.info(f"Blood pressure saved: {systolic}/{diastolic} (MAP: {map_value})")
    return bp.id

# --- Temperature CRUD ---
def save_temperature(db: Session, skin_temp, body_temp, raw_data):
    """
    Save temperature reading to database (Postgres)
    """
    now = datetime.now()
    temp = Temperature(
        timestamp=now,
        skin_temp=skin_temp,
        body_temp=body_temp,
        raw_data=raw_data,
        created_at=now
    )
    db.add(temp)
    db.commit()
    db.refresh(temp)
    logger.info(f"Temperature saved: Skin: {skin_temp}°, Body: {body_temp}°")
    return temp.id

# --- Generic Vital CRUD ---
def save_vital(db: Session, vital_type, value, timestamp=None, notes=None, vital_group=None):
    """
    Save a generic vital reading to database (Postgres)
    """
    now = datetime.now()
    ts = timestamp or now
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

# --- Get Distinct Vital Types ---
def get_distinct_vital_types(db: Session):
    logger.info(f"DB connection: {db.bind.url}")
    logger.info("Fetching distinct vital types...")
    types = db.query(Vital.vital_type).filter(Vital.vital_type.isnot(None)).filter(Vital.vital_type != '').distinct().all()
    logger.info(f"Distinct vital types fetched: {types}")
    return [t[0] for t in types]

# --- Paginated Vital History ---
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

# Add other CRUD functions as needed, following the same pattern and using SQLAlchemy ORM.
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
def save_setting(db: Session, key, value, data_type="string", description=None):
    """
    Save a setting to the database

    Args:
        key (str): Setting key/name
        value (any): Setting value (will be converted to string)
        data_type (str): Data type (string, int, float, bool, json)
        description (str, optional): Description of the setting
    """
    try:
        now = datetime.now().isoformat()

        # Convert value to string for storage
        str_value = str(value)

        # Check if setting exists
        exists = db.query(Setting).filter(Setting.key == key).first() is not None

        if exists:
            db.query(Setting).filter(Setting.key == key).update({
                Setting.value: str_value,
                Setting.data_type: data_type,
                Setting.description: description,
                Setting.updated_at: now
            })
        else:
            new_setting = Setting(
                key=key,
                value=str_value,
                data_type=data_type,
                description=description,
                updated_at=now
            )
            db.add(new_setting)

        db.commit()
        logger.info(f"Setting saved: {key}={value}")
        return True
    except Exception as e:
        logger.error(f"Error saving setting: {e}")
        return False
def get_setting(db: Session, key, default=None):
    """
    Get a setting from the database with proper type conversion

    Args:
        key (str): Setting key/name
        default (any, optional): Default value if setting not found

    Returns:
        any: The setting value with proper type conversion
    """
    try:
        row = db.query(Setting).filter(Setting.key == key).first()

        if not row:
            return default

        value = row.value
        data_type = row.data_type

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

    except Exception as e:
        logger.error(f"Error fetching setting {key}: {e}")
        return default
def get_all_settings(db: Session):
    """
    Get all settings from the database

    Returns:
        dict: Dictionary of all settings with proper type conversion
    """
    try:
        rows = db.query(Setting).all()

        settings = {}
        for row in rows:
            key = row.key
            value = row.value
            data_type = row.data_type

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
                'description': row.description,
                'updated_at': row.updated_at
            }

        return settings

    except Exception as e:
        logger.error(f"Error fetching all settings: {e}")
        return {}
def delete_setting(db: Session, key):
    """
    Delete a setting from the database

    Args:
        key (str): Setting key/name

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        result = db.query(Setting).filter(Setting.key == key).delete()
        db.commit()

        if result:
            logger.info(f"Setting deleted: {key}")
        else:
            logger.info(f"Setting not found for deletion: {key}")

        return result > 0
    except Exception as e:
        logger.error(f"Error deleting setting {key}: {e}")
        return False
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
def start_monitoring_alert(db: Session, spo2=None, bpm=None, data_id=None, spo2_alarm_triggered=None, hr_alarm_triggered=None, external_alarm_triggered=None):
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
        now = datetime.now().isoformat()

        alert = MonitoringAlert(
            start_time=now,
            start_data_id=data_id,
            spo2_min=spo2,
            spo2_max=spo2,
            bpm_min=bpm,
            bpm_max=bpm,
            spo2_alarm_triggered=spo2_alarm_triggered,
            hr_alarm_triggered=hr_alarm_triggered,
            created_at=now
        )

        db.add(alert)
        db.commit()
        db.refresh(alert)
        logger.info(f"Started monitoring alert #{alert.id} - SpO2: {spo2}%, BPM: {bpm}")
        return alert.id
    except Exception as e:
        logger.error(f"Error starting monitoring alert: {e}")
        return None
def update_monitoring_alert(db: Session, alert_id, end_time=None, end_data_id=None, spo2=None, bpm=None,
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
        # First, get current values
        alert = db.query(MonitoringAlert).filter(MonitoringAlert.id == alert_id).first()

        if not alert:
            logger.error(f"Alert ID {alert_id} not found for update")
            return False

        current_spo2_min = alert.spo2_min
        current_spo2_max = alert.spo2_max
        current_bpm_min = alert.bpm_min
        current_bpm_max = alert.bpm_max

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
        update_fields = {}

        if end_time:
            update_fields[MonitoringAlert.end_time] = end_time

        if end_data_id:
            update_fields[MonitoringAlert.end_data_id] = end_data_id

        if spo2 is not None:
            update_fields[MonitoringAlert.spo2_min] = current_spo2_min
            update_fields[MonitoringAlert.spo2_max] = current_spo2_max

        if bpm is not None:
            update_fields[MonitoringAlert.bpm_min] = current_bpm_min
            update_fields[MonitoringAlert.bpm_max] = current_bpm_max

        if spo2_alarm_triggered is not None:
            update_fields[MonitoringAlert.spo2_alarm_triggered] = spo2_alarm_triggered

        if hr_alarm_triggered is not None:
            update_fields[MonitoringAlert.hr_alarm_triggered] = hr_alarm_triggered

        if external_alarm_triggered is not None:
            update_fields[MonitoringAlert.external_alarm_triggered] = external_alarm_triggered

        if oxygen_used is not None:
            update_fields[MonitoringAlert.oxygen_used] = oxygen_used

        if oxygen_highest is not None:
            update_fields[MonitoringAlert.oxygen_highest] = oxygen_highest

        if oxygen_unit is not None:
            update_fields[MonitoringAlert.oxygen_unit] = oxygen_unit

        if not update_fields:
            logger.warning("No fields to update for alert")
            return True

        db.query(MonitoringAlert).filter(MonitoringAlert.id == alert_id).update(update_fields)
        db.commit()

        logger.info(f"Updated monitoring alert #{alert_id}")
        return True
    except Exception as e:
        logger.error(f"Error updating monitoring alert: {e}")
        return False
def acknowledge_alert(db: Session, alert_id):
    """
    Mark an alert as acknowledged

    Args:
        alert_id (int): ID of the alert to acknowledge

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        result = db.query(MonitoringAlert).filter(MonitoringAlert.id == alert_id).update({
            MonitoringAlert.acknowledged: True
        })
        db.commit()

        success = result > 0
        if success:
            logger.info(f"Alert #{alert_id} acknowledged")
        else:
            logger.warning(f"Alert #{alert_id} not found for acknowledgment")

        return success
    except Exception as e:
        logger.error(f"Error acknowledging alert: {e}")
        return False
def get_unacknowledged_alerts_count(db: Session):
    """
    Get count of unacknowledged alerts

    Returns:
        int: Number of unacknowledged alerts
    """
    try:
        count = db.query(MonitoringAlert).filter(MonitoringAlert.acknowledged == False).count()
        return count
    except Exception as e:
        logger.error(f"Error getting unacknowledged alert count: {e}")
        db.rollback()  # Rollback the transaction on error
        return 0
def get_monitoring_alerts(db: Session, limit=50, include_acknowledged=False, detailed=False):
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
        query = db.query(MonitoringAlert)

        if not include_acknowledged:
            query = query.filter(MonitoringAlert.acknowledged == False)

        query = query.order_by(MonitoringAlert.start_time.desc()).limit(limit)

        results = query.all()
        alerts = []

        for row in results:
            alert = {
                'id': row.id,
                'start_time': row.start_time,
                'end_time': row.end_time,
                'start_data_id': row.start_data_id,
                'end_data_id': row.end_data_id,
                'spo2_min': row.spo2_min,
                'spo2_max': row.spo2_max,
                'bpm_min': row.bpm_min,
                'bpm_max': row.bpm_max,
                'spo2_alarm_triggered': row.spo2_alarm_triggered,
                'hr_alarm_triggered': row.hr_alarm_triggered,
                'external_alarm_triggered': row.external_alarm_triggered,
                'oxygen_used': row.oxygen_used,
                'oxygen_highest': row.oxygen_highest,
                'oxygen_unit': row.oxygen_unit,
                'acknowledged': row.acknowledged,
                'created_at': row.created_at
            }

            if detailed and row.start_data_id:
                # Get all pulse ox data between start and end
                data_query = db.query(PulseOxData).filter(
                    PulseOxData.id >= row.start_data_id,
                    (row.end_data_id is None) | (PulseOxData.id <= row.end_data_id)
                ).order_by(PulseOxData.timestamp.asc())

                data_results = data_query.all()
                alert['data_points'] = [
                    {
                        'id': data_row.id,
                        'timestamp': data_row.timestamp,
                        'spo2': data_row.spo2,
                        'bpm': data_row.bpm,
                        'pa': data_row.pa,
                        'status': data_row.status,
                        'motion': data_row.motion,
                        'spo2_alarm': data_row.spo2_alarm == 'ON',
                        'hr_alarm': data_row.hr_alarm == 'ON',
                        'perfusion': data_row.pa  # Rename pa to perfusion
                    }
                    for data_row in data_results
                ]

            alerts.append(alert)

        return alerts
    except Exception as e:
        logger.error(f"Error fetching monitoring alerts: {e}")
        return []

def add_equipment(db: Session, name, quantity=1, scheduled_replacement=True, last_changed=None, useful_days=None):
    try:
        equipment = Equipment(
            name=name,
            quantity=quantity,
            scheduled_replacement=scheduled_replacement,
            last_changed=last_changed if scheduled_replacement else None,
            useful_days=useful_days if scheduled_replacement else None
        )
        db.add(equipment)
        db.commit()
        db.refresh(equipment)
        logger.info(f"Equipment added: {name}")
        return equipment.id
    except Exception as e:
        logger.error(f"Error adding equipment: {e}")
        return None
def get_equipment_list(db: Session):
    try:
        equipment = db.query(Equipment).all()
        result = []
        for item in equipment:
            item_dict = {
                'id': item.id,
                'name': item.name,
                'quantity': item.quantity,
                'scheduled_replacement': item.scheduled_replacement,
                'last_changed': item.last_changed,
                'useful_days': item.useful_days,
                'due_date': None
            }
            
            # Only calculate due date if scheduled replacement is enabled
            if item.scheduled_replacement and item.last_changed and item.useful_days:
                from datetime import datetime, timedelta
                if isinstance(item.last_changed, str):
                    last = datetime.fromisoformat(item.last_changed)
                else:
                    last = item.last_changed
                due = last + timedelta(days=item.useful_days)
                item_dict['due_date'] = due.isoformat()
            
            result.append(item_dict)
        
        # Sort by due_date (scheduled items first, then by due date)
        def sort_key(x):
            if not x['scheduled_replacement']:
                return (1, x['name'])  # Non-scheduled items go to end, sorted by name
            elif x['due_date']:
                return (0, x['due_date'])  # Scheduled items sorted by due date
            else:
                return (0, '9999-12-31')  # Scheduled items without due date go to end of scheduled
        
        result.sort(key=sort_key)
        return result
    except Exception as e:
        logger.error(f"Error fetching equipment: {e}")
        return []
def log_equipment_change(db: Session, equipment_id, changed_at):
    try:
        change_log = EquipmentChangeLog(
            equipment_id=equipment_id,
            changed_at=changed_at
        )
        db.add(change_log)

        # Update last_changed in equipment
        db.query(Equipment).filter(Equipment.id == equipment_id).update({
            Equipment.last_changed: changed_at
        })

        db.commit()
        logger.info(f"Equipment change logged for ID {equipment_id}")
        return True
    except Exception as e:
        logger.error(f"Error logging equipment change: {e}")
        return False
def get_equipment_change_history(db: Session, equipment_id):
    try:
        changes = db.query(EquipmentChangeLog).filter(EquipmentChangeLog.equipment_id == equipment_id).order_by(EquipmentChangeLog.changed_at.desc()).all()
        return changes
    except Exception as e:
        logger.error(f"Error fetching equipment change history: {e}")
        return []
def get_pulse_ox_data_for_alert(db: Session, alert_id):
    """
    Get all pulse ox readings associated with an alert event

    Args:
        alert_id: The ID of the alert

    Returns:
        List of pulse ox readings during the alert period
    """
    try:
        # First get the alert to determine the time period
        alert = db.query(MonitoringAlert).filter(MonitoringAlert.id == alert_id).first()

        if not alert:
            return []

        start_time = alert.start_time
        end_time = alert.end_time or datetime.now().isoformat()

        # Get pulse ox data between the start and end times of the alert
        data = db.query(PulseOxData).filter(
            PulseOxData.timestamp >= start_time,
            PulseOxData.timestamp <= end_time
        ).order_by(PulseOxData.timestamp.asc()).all()

        for row in data:
            # Convert spo2_alarm and hr_alarm to booleans
            row.spo2_alarm = row.spo2_alarm == 'ON'
            row.hr_alarm = row.hr_alarm == 'ON'
            # Rename columns for frontend consistency
            row.perfusion = row.pa  # Rename pa to perfusion

        return data
    except Exception as e:
        logger.error(f"Error fetching pulse ox data for alert {alert_id}: {e}")
        return []
def record_ventilator_alarm(db: Session, device_id, pin):
    """Record a ventilator alarm event in the database"""
    try:
        now = datetime.now().isoformat()

        # Check for an existing active vent alarm
        existing_alert = db.query(VentilatorAlert).filter(
            VentilatorAlert.end_time == None,
            VentilatorAlert.device_id == device_id
        ).first()

        if existing_alert:
            # Update the existing alert with new activity
            db.query(VentilatorAlert).filter(VentilatorAlert.id == existing_alert.id).update({
                VentilatorAlert.last_activity: now
            })
        else:
            # Create a new alert
            alert = VentilatorAlert(
                device_id=device_id,
                pin=pin,
                start_time=now,
                last_activity=now,
                acknowledged=False
            )
            db.add(alert)

        db.commit()
        logger.info(f"Ventilator alarm recorded for {device_id} on pin {pin}")
        return True
    except Exception as e:
        logger.error(f"Database error recording ventilator alarm: {e}")
        return False
def record_external_pulse_ox_alarm(db: Session, device_id, pin):
    """Record an external pulse oximeter alarm event in the database"""
    try:
        now = datetime.now().isoformat()

        # Start a new monitoring alert with external trigger flag
        alert = MonitoringAlert(
            start_time=now,
            external_alarm_triggered=True,
            created_at=now
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)

        # Also record detailed alarm info in a dedicated table
        external_alarm = ExternalAlarm(
            alert_id=alert.id,
            device_id=device_id,
            pin=pin,
            start_time=now,
            last_activity=now
        )
        db.add(external_alarm)

        db.commit()
        logger.info(f"External pulse ox alarm recorded for {device_id} on pin {pin}, alert ID: {alert.id}")
        return alert.id
    except Exception as e:
        logger.error(f"Database error recording external pulse ox alarm: {e}")
        return None
def clear_external_alarm(db: Session, device_id):
    """Close any active external alarms for the given device"""
    try:
        now = datetime.now().isoformat()

        # First find which device type this is
        device_type = get_setting(f"{device_id}_device", "unknown")

        if device_type == "vent":
            # Close any active ventilator alerts
            db.query(VentilatorAlert).filter(
                VentilatorAlert.device_id == device_id,
                VentilatorAlert.end_time == None
            ).update({
                VentilatorAlert.end_time: now
            })
        elif device_type == "pulseox":
            # Get all active external alarms for this device
            active_alarms = db.query(ExternalAlarm).filter(
                ExternalAlarm.device_id == device_id,
                ExternalAlarm.end_time == None
            ).all()

            # Close the external alarms
            for alarm in active_alarms:
                alarm.end_time = now
                db.add(alarm)

            # Also update the monitoring alerts
            for alarm in active_alarms:
                db.query(MonitoringAlert).filter(
                    MonitoringAlert.id == alarm.alert_id,
                    MonitoringAlert.end_time == None
                ).update({
                    MonitoringAlert.end_time: now
                })

        db.commit()
        logger.info(f"External alarm cleared for {device_id} ({device_type})")
        return True
    except Exception as e:
        logger.error(f"Database error clearing external alarm: {e}")
        return False
def get_equipment_due_count(db: Session):
    """Return the count of equipment items where due_date is today or past."""
    try:
        equipment = db.query(Equipment).filter(Equipment.scheduled_replacement == True).all()
        from datetime import datetime, timedelta
        due_count = 0
        today = datetime.now().date()
        for item in equipment:
            if item.last_changed and item.useful_days:
                if isinstance(item.last_changed, str):
                    last = datetime.fromisoformat(item.last_changed)
                else:
                    last = item.last_changed
                due_date = (last.date() if hasattr(last, 'date') else last) + timedelta(days=item.useful_days)
                if due_date <= today:
                    due_count += 1
        return due_count
    except Exception as e:
        logger.error(f"Error calculating equipment due count: {e}")
        db.rollback()  # Rollback the transaction on error
        return 0
def add_medication(db: Session, name, concentration=None, quantity=None, quantity_unit=None, instructions=None, start_date=None, end_date=None, as_needed=False, notes=None, active=True):
    """
    Add a new medication to the database.
    """
    from datetime import datetime
    now = datetime.now()
    medication = Medication(
        name=name,
        concentration=concentration,
        quantity=quantity,
        quantity_unit=quantity_unit,
        instructions=instructions,
        start_date=start_date,
        end_date=end_date,
        as_needed=as_needed,
        notes=notes,
        active=active,
        created_at=now,
        updated_at=now
    )
    db.add(medication)
    db.commit()
    db.refresh(medication)
    logger.info(f"Medication added: {name}")
    return medication.id

def get_active_medications(db: Session):
    """
    Get all active medications (active=True and end_date is None or > today)
    """
    try:
        from datetime import datetime
        today = datetime.now().date()
        
        medications = db.query(Medication).filter(
            Medication.active == True,
            (Medication.end_date == None) | (Medication.end_date > today)
        ).order_by(Medication.name).all()
        
        return [
            {
                'id': med.id,
                'name': med.name,
                'concentration': med.concentration,
                'quantity': med.quantity,
                'quantity_unit': med.quantity_unit,
                'instructions': med.instructions,
                'start_date': med.start_date.isoformat() if med.start_date else None,
                'end_date': med.end_date.isoformat() if med.end_date else None,
                'as_needed': med.as_needed,
                'notes': med.notes,
                'active': med.active,
                'created_at': med.created_at.isoformat() if med.created_at else None,
                'updated_at': med.updated_at.isoformat() if med.updated_at else None,
                'schedules': []  # TODO: Add schedules when implemented
            }
            for med in medications
        ]
    except Exception as e:
        logger.error(f"Error fetching active medications: {e}")
        return []

def get_inactive_medications(db: Session):
    """
    Get all inactive medications (active=False or end_date <= today)
    """
    try:
        from datetime import datetime
        today = datetime.now().date()
        
        medications = db.query(Medication).filter(
            (Medication.active == False) | (Medication.end_date <= today)
        ).order_by(Medication.name).all()
        
        return [
            {
                'id': med.id,
                'name': med.name,
                'concentration': med.concentration,
                'quantity': med.quantity,
                'quantity_unit': med.quantity_unit,
                'instructions': med.instructions,
                'start_date': med.start_date.isoformat() if med.start_date else None,
                'end_date': med.end_date.isoformat() if med.end_date else None,
                'as_needed': med.as_needed,
                'notes': med.notes,
                'active': med.active,
                'created_at': med.created_at.isoformat() if med.created_at else None,
                'updated_at': med.updated_at.isoformat() if med.updated_at else None,
                'schedules': []  # TODO: Add schedules when implemented
            }
            for med in medications
        ]
    except Exception as e:
        logger.error(f"Error fetching inactive medications: {e}")
        return []

def update_medication(db: Session, med_id, **kwargs):
    """
    Update an existing medication
    """
    try:
        from datetime import datetime
        
        # Get the medication
        medication = db.query(Medication).filter(Medication.id == med_id).first()
        if not medication:
            logger.error(f"Medication ID {med_id} not found for update")
            return False
        
        # Update fields
        for key, value in kwargs.items():
            if hasattr(medication, key):
                setattr(medication, key, value)
        
        medication.updated_at = datetime.now()
        
        db.commit()
        logger.info(f"Medication updated: {medication.name}")
        return True
    except Exception as e:
        logger.error(f"Error updating medication: {e}")
        return False

def delete_medication(db: Session, med_id):
    """
    Delete a medication (soft delete by setting active=False)
    """
    try:
        medication = db.query(Medication).filter(Medication.id == med_id).first()
        if medication:
            medication.active = False
            medication.updated_at = datetime.now()
            db.commit()
            logger.info(f"Medication {med_id} deleted (soft delete)")
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting medication {med_id}: {e}")
        db.rollback()
        return False

# --- MedicationSchedule CRUD ---

def add_medication_schedule(db: Session, medication_id, cron_expression, description=None, dose_amount=None, active=True, notes=None):
    """
    Add a new medication schedule
    """
    try:
        now = datetime.now()
        schedule = MedicationSchedule(
            medication_id=medication_id,
            cron_expression=cron_expression,
            description=description,
            dose_amount=dose_amount,
            active=active,
            notes=notes,
            created_at=now,
            updated_at=now
        )
        db.add(schedule)
        db.commit()
        db.refresh(schedule)
        logger.info(f"Medication schedule added for medication {medication_id}: {cron_expression}")
        return schedule.id
    except Exception as e:
        logger.error(f"Error adding medication schedule: {e}")
        db.rollback()
        return None

def get_medication_schedules(db: Session, medication_id):
    """
    Get all schedules for a specific medication
    """
    try:
        schedules = db.query(MedicationSchedule).filter(
            MedicationSchedule.medication_id == medication_id
        ).order_by(MedicationSchedule.created_at.desc()).all()
        
        return [
            {
                'id': s.id,
                'medication_id': s.medication_id,
                'cron_expression': s.cron_expression,
                'description': s.description,
                'dose_amount': s.dose_amount,
                'active': s.active,
                'notes': s.notes,
                'created_at': s.created_at,
                'updated_at': s.updated_at
            }
            for s in schedules
        ]
    except Exception as e:
        logger.error(f"Error fetching medication schedules for medication {medication_id}: {e}")
        return []

def get_all_medication_schedules(db: Session, active_only=True):
    """
    Get all medication schedules, optionally filtering by active status
    """
    try:
        query = db.query(MedicationSchedule)
        if active_only:
            query = query.filter(MedicationSchedule.active == True)
        
        schedules = query.order_by(MedicationSchedule.created_at.desc()).all()
        
        return [
            {
                'id': s.id,
                'medication_id': s.medication_id,
                'cron_expression': s.cron_expression,
                'description': s.description,
                'dose_amount': s.dose_amount,
                'active': s.active,
                'notes': s.notes,
                'created_at': s.created_at,
                'updated_at': s.updated_at
            }
            for s in schedules
        ]
    except Exception as e:
        logger.error(f"Error fetching all medication schedules: {e}")
        return []

def update_medication_schedule(db: Session, schedule_id, **kwargs):
    """
    Update an existing medication schedule
    """
    try:
        schedule = db.query(MedicationSchedule).filter(MedicationSchedule.id == schedule_id).first()
        if not schedule:
            logger.warning(f"Medication schedule {schedule_id} not found")
            return False
        
        # Update fields if provided
        for key, value in kwargs.items():
            if hasattr(schedule, key):
                setattr(schedule, key, value)
        
        schedule.updated_at = datetime.now()
        db.commit()
        logger.info(f"Medication schedule {schedule_id} updated")
        return True
    except Exception as e:
        logger.error(f"Error updating medication schedule {schedule_id}: {e}")
        db.rollback()
        return False

def delete_medication_schedule(db: Session, schedule_id):
    """
    Delete a medication schedule (hard delete since it's not critical data)
    """
    try:
        schedule = db.query(MedicationSchedule).filter(MedicationSchedule.id == schedule_id).first()
        if not schedule:
            logger.warning(f"Medication schedule {schedule_id} not found")
            return False
        
        db.delete(schedule)
        db.commit()
        logger.info(f"Medication schedule {schedule_id} deleted")
        return True
    except Exception as e:
        logger.error(f"Error deleting medication schedule {schedule_id}: {e}")
        db.rollback()
        return False

def toggle_medication_schedule_active(db: Session, schedule_id):
    """
    Toggle the active status of a medication schedule
    """
    try:
        schedule = db.query(MedicationSchedule).filter(MedicationSchedule.id == schedule_id).first()
        if not schedule:
            logger.warning(f"Medication schedule {schedule_id} not found")
            return False, None
        
        schedule.active = not schedule.active
        schedule.updated_at = datetime.now()
        db.commit()
        logger.info(f"Medication schedule {schedule_id} active status toggled to {schedule.active}")
        return True, schedule.active
    except Exception as e:
        logger.error(f"Error toggling medication schedule {schedule_id}: {e}")
        db.rollback()
        return False, None
def get_scheduled_medications_for_date(db: Session, target_date=None):
    """
    Get all medications scheduled for a specific date
    
    Args:
        target_date: datetime.date object, defaults to today
    
    Returns:
        List of scheduled medication entries with calculated times
    """
    try:
        if target_date is None:
            target_date = datetime.now().date()
        
        # Get all active medication schedules
        schedules = db.query(MedicationSchedule).filter(
            MedicationSchedule.active == True
        ).join(Medication).filter(
            Medication.active == True
        ).all()
        
        scheduled_meds = []
        
        for schedule in schedules:
            try:
                # Create datetime for start of target date
                start_of_day = datetime.combine(target_date, datetime.min.time())
                end_of_day = datetime.combine(target_date, datetime.max.time())
                
                # Initialize croniter with a time before the target date
                base_time = start_of_day - timedelta(days=1)
                cron = croniter(schedule.cron_expression, base_time)
                
                # Find all scheduled times for the target date
                while True:
                    next_time = cron.get_next(datetime)
                    if next_time.date() > target_date:
                        break
                    if next_time.date() == target_date:
                        scheduled_meds.append({
                            'schedule_id': schedule.id,
                            'medication_id': schedule.medication_id,
                            'medication_name': schedule.medication.name,
                            'dose_amount': schedule.dose_amount,
                            'dose_unit': schedule.medication.quantity_unit,
                            'scheduled_time': next_time,
                            'description': schedule.description,
                            'cron_expression': schedule.cron_expression
                        })
            except Exception as cron_error:
                logger.error(f"Error processing cron expression {schedule.cron_expression}: {cron_error}")
                continue
        
        return sorted(scheduled_meds, key=lambda x: x['scheduled_time'])
        
    except Exception as e:
        logger.error(f"Error getting scheduled medications: {e}")
        return []

def get_missed_medications(db: Session, target_date=None):
    """
    Get medications that were scheduled but not taken for a specific date
    
    Args:
        target_date: datetime.date object, defaults to yesterday
    
    Returns:
        List of missed medication entries
    """
    try:
        if target_date is None:
            target_date = (datetime.now() - timedelta(days=1)).date()
        
        # Get all scheduled medications for the target date
        scheduled = get_scheduled_medications_for_date(db, target_date)
        
        missed_meds = []
        
        for scheduled_med in scheduled:
            # Check if this scheduled dose was logged
            scheduled_time = scheduled_med['scheduled_time']
            schedule_id = scheduled_med['schedule_id']
            
            # Look for a log entry within a reasonable window (e.g., ±2 hours)
            time_window_start = scheduled_time - timedelta(hours=2)
            time_window_end = scheduled_time + timedelta(hours=2)
            
            log_entry = db.query(MedicationLog).filter(
                MedicationLog.schedule_id == schedule_id,
                MedicationLog.administered_at >= time_window_start,
                MedicationLog.administered_at <= time_window_end
            ).first()
            
            if not log_entry:
                # This scheduled dose was missed
                missed_meds.append({
                    **scheduled_med,
                    'missed_date': target_date,
                    'status': 'missed'
                })
        
        return missed_meds
        
    except Exception as e:
        logger.error(f"Error getting missed medications: {e}")
        return []

def get_daily_medication_schedule(db: Session):
    """
    Get scheduled medications for today and yesterday in chronological order with status
    
    Returns:
        Dict with 'scheduled_medications' list sorted chronologically
    """
    try:
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        current_time = datetime.now()
        
        # Get scheduled meds for yesterday and today
        yesterday_scheduled = get_scheduled_medications_for_date(db, yesterday)
        today_scheduled = get_scheduled_medications_for_date(db, today)
        
        all_scheduled = []
        
        # Process yesterday's schedules (check if missed)
        for item in yesterday_scheduled:
            scheduled_time = item['scheduled_time']
            schedule_id = item['schedule_id']
            
            # Check if this was taken - look for any log entry for this schedule and date
            # First try exact schedule_id match
            log_entry = db.query(MedicationLog).filter(
                MedicationLog.schedule_id == schedule_id,
                MedicationLog.scheduled_time == scheduled_time
            ).first()
            
            # If no exact match, check within time window (±4 hours for more flexibility)
            if not log_entry:
                time_window_start = scheduled_time - timedelta(hours=4)
                time_window_end = scheduled_time + timedelta(hours=4)
                
                log_entry = db.query(MedicationLog).filter(
                    MedicationLog.schedule_id == schedule_id,
                    MedicationLog.administered_at >= time_window_start,
                    MedicationLog.administered_at <= time_window_end
                ).first()
            
            if log_entry:
                # Check if dose was skipped (actual_dose = 0)
                if log_entry.dose_amount == 0:
                    status = 'skipped'
                else:
                    # Calculate timing status for completed dose
                    # Ensure both datetimes are timezone-naive for comparison
                    administered_at = log_entry.administered_at
                    if administered_at.tzinfo is not None:
                        administered_at = administered_at.replace(tzinfo=None)
                    
                    scheduled_time_naive = scheduled_time
                    if scheduled_time_naive.tzinfo is not None:
                        scheduled_time_naive = scheduled_time_naive.replace(tzinfo=None)
                    
                    time_diff = (administered_at - scheduled_time_naive).total_seconds() / 60  # minutes
                    if abs(time_diff) <= 60:  # Within 1 hour
                        status = 'completed_on_time'
                    elif abs(time_diff) <= 120:  # 1-2 hours early/late
                        status = 'completed_warning'
                    else:  # More than 2 hours early/late
                        status = 'completed_late'
                
                # Show all completed medications from yesterday (including on-time ones)
                all_scheduled.append({
                    **item,
                    'status': status,
                    'administered_at': log_entry.administered_at,
                    'actual_dose': log_entry.dose_amount,
                    'is_completed': True
                })
            else:
                # Show as missed if it's from yesterday or earlier
                if scheduled_time.date() < today:
                    all_scheduled.append({
                        **item,
                        'status': 'missed',
                        'is_completed': False
                    })
        
        # Process today's schedules
        for item in today_scheduled:
            scheduled_time = item['scheduled_time']
            schedule_id = item['schedule_id']
            
            # Check if this was taken - look for any log entry for this schedule and date
            # First try exact schedule_id and scheduled_time match
            log_entry = db.query(MedicationLog).filter(
                MedicationLog.schedule_id == schedule_id,
                MedicationLog.scheduled_time == scheduled_time
            ).first()
            
            # If no exact match, check within time window (±4 hours for more flexibility)
            if not log_entry:
                time_window_start = scheduled_time - timedelta(hours=4)
                time_window_end = scheduled_time + timedelta(hours=4)
                
                log_entry = db.query(MedicationLog).filter(
                    MedicationLog.schedule_id == schedule_id,
                    MedicationLog.administered_at >= time_window_start,
                    MedicationLog.administered_at <= time_window_end
                ).first()
            
            if log_entry:
                # Check if dose was skipped (actual_dose = 0)
                if log_entry.dose_amount == 0:
                    status = 'skipped'
                else:
                    # Calculate timing status for completed dose
                    # Ensure both datetimes are timezone-naive for comparison
                    administered_at = log_entry.administered_at
                    if administered_at.tzinfo is not None:
                        administered_at = administered_at.replace(tzinfo=None)
                    
                    scheduled_time_naive = scheduled_time
                    if scheduled_time_naive.tzinfo is not None:
                        scheduled_time_naive = scheduled_time_naive.replace(tzinfo=None)
                    
                    time_diff = (administered_at - scheduled_time_naive).total_seconds() / 60  # minutes
                    if abs(time_diff) <= 60:  # Within 1 hour
                        status = 'completed_on_time'
                    elif abs(time_diff) <= 120:  # 1-2 hours early/late
                        status = 'completed_warning'
                    else:  # More than 2 hours early/late
                        status = 'completed_late'
                
                all_scheduled.append({
                    **item,
                    'status': status,
                    'administered_at': log_entry.administered_at,
                    'actual_dose': log_entry.dose_amount,
                    'is_completed': True
                })
            else:
                # Check timing status for pending dose
                # Ensure both datetimes are timezone-naive for comparison
                current_time_naive = current_time
                if current_time_naive.tzinfo is not None:
                    current_time_naive = current_time_naive.replace(tzinfo=None)
                
                scheduled_time_naive = scheduled_time
                if scheduled_time_naive.tzinfo is not None:
                    scheduled_time_naive = scheduled_time_naive.replace(tzinfo=None)
                
                time_diff = (current_time_naive - scheduled_time_naive).total_seconds() / 60  # minutes
                
                if scheduled_time_naive > current_time_naive:
                    # Future dose
                    status = 'pending'
                elif time_diff <= 60:
                    # Within 1 hour of scheduled time
                    status = 'due_on_time'
                elif time_diff <= 120:
                    # 1-2 hours late
                    status = 'due_warning'
                else:
                    # More than 2 hours late
                    status = 'due_late'
                
                all_scheduled.append({
                    **item,
                    'status': status,
                    'is_completed': False
                })
        
        # Sort by scheduled time chronologically
        all_scheduled.sort(key=lambda x: x['scheduled_time'])
        
        return {
            'scheduled_medications': all_scheduled,
            'generated_at': current_time.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting daily medication schedule: {e}")
        return {
            'scheduled_medications': [],
            'generated_at': datetime.now().isoformat()
        }
def get_due_and_upcoming_medications_count(db):
    """
    Returns the count of scheduled medications that are:
    - missed (for today or yesterday)
    - due_late or due_warning (for today or yesterday)
    - due_on_time or pending (for today or yesterday) and scheduled within the next hour
    """
    try:
        schedule_data = get_daily_medication_schedule(db)
        meds = schedule_data.get('scheduled_medications', [])
        now = datetime.now()
        count = 0
        for med in meds:
            status = med.get('status')
            scheduled_time = med.get('scheduled_time')
            if status in ('missed', 'due_warning', 'due_late'):
                count += 1
            elif status in ('due_on_time', 'pending') and scheduled_time:
                # Only count if within 1 hour from now
                if isinstance(scheduled_time, str):
                    try:
                        scheduled_time = datetime.fromisoformat(scheduled_time)
                    except Exception:
                        continue
                delta = (scheduled_time - now).total_seconds() / 60  # minutes
                if 0 <= delta <= 60:
                    count += 1
        return count
    except Exception as e:
        logger.error(f"Error getting due/upcoming medications count: {e}")
        return 0
def receive_equipment(db: Session, equipment_id: int, amount: int = 1):
    try:
        equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
        if not equipment:
            return False
        equipment.quantity += amount
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Error receiving equipment: {e}")
        return False

def open_equipment(db: Session, equipment_id: int, amount: int = 1):
    """Deduct equipment quantity (open/use equipment) and log the action."""
    try:
        equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
        if not equipment:
            return False
        
        # Check if enough quantity is available
        if equipment.quantity < amount:
            return False
            
        # Deduct quantity
        equipment.quantity -= amount
        
        # Update last_changed date
        from datetime import datetime
        equipment.last_changed = datetime.now()
        
        # Log the action in equipment change history
        change_log = EquipmentChangeLog(
            equipment_id=equipment_id,
            changed_at=datetime.now()
        )
        db.add(change_log)
        
        db.commit()
        logger.info(f"Equipment opened/used for ID {equipment_id}, quantity deducted: {amount}")
        return True
    except Exception as e:
        logger.error(f"Error opening equipment: {e}")
        db.rollback()
        return False
def administer_medication(db: Session, med_id, dose_amount, schedule_id=None, scheduled_time=None, notes=None):
    try:
        med = db.query(Medication).filter(Medication.id == med_id).first()
        if not med or med.quantity is None or dose_amount is None:
            return False
        
        # Only deduct from quantity if dose_amount > 0 (don't deduct for skipped doses)
        if float(dose_amount) > 0:
            med.quantity = float(med.quantity) - float(dose_amount)
        
        # Calculate timing flags if this is a scheduled dose
        administered_early = False
        administered_late = False
        
        if schedule_id and scheduled_time:
            from datetime import datetime
            administered_at = datetime.now()
            
            # Parse scheduled_time if it's a string
            if isinstance(scheduled_time, str):
                try:
                    scheduled_time = datetime.fromisoformat(scheduled_time.replace('Z', '+00:00'))
                except:
                    scheduled_time = datetime.fromisoformat(scheduled_time)
            
            # Make both timezone-naive for comparison
            if administered_at.tzinfo is not None:
                administered_at = administered_at.replace(tzinfo=None)
            if scheduled_time.tzinfo is not None:
                scheduled_time = scheduled_time.replace(tzinfo=None)
            
            # Calculate time difference in minutes
            time_diff_minutes = (administered_at - scheduled_time).total_seconds() / 60
            
            # Set flags based on timing (more than 60 minutes off is considered early/late)
            if time_diff_minutes < -60:  # Administered more than 60 minutes early
                administered_early = True
            elif time_diff_minutes > 60:  # Administered more than 60 minutes late
                administered_late = True
        
        # Record log
        from datetime import datetime
        log = MedicationLog(
            medication_id=med_id,
            schedule_id=schedule_id,
            administered_at=datetime.now(),
            dose_amount=dose_amount,
            is_scheduled=bool(schedule_id),
            scheduled_time=scheduled_time,
            administered_early=administered_early,
            administered_late=administered_late,
            notes=notes,
            created_at=datetime.now()
        )
        db.add(log)
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Error administering medication: {e}")
        db.rollback()
        return False
def get_medication_history(db: Session, limit=25, medication_name=None, start_date=None, end_date=None, status_filter=None):
    """
    Get medication administration history with filtering options
    
    Args:
        db: Database session
        limit: Maximum number of records to return (default 25)
        medication_name: Filter by medication name (partial match)
        start_date: Filter by start date (YYYY-MM-DD format)
        end_date: Filter by end date (YYYY-MM-DD format)  
        status_filter: Filter by status ('late', 'early', 'missed', 'on-time')
    
    Returns:
        List of medication administration records with related data
    """
    try:
        # Start with base query joining medication log with medication and schedule
        query = db.query(MedicationLog).join(Medication).outerjoin(MedicationSchedule)
        
        # Filter by medication name (partial match, case insensitive)
        if medication_name:
            query = query.filter(Medication.name.ilike(f'%{medication_name}%'))
        
        # Filter by date range
        if start_date:
            start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(MedicationLog.administered_at >= start_datetime)
        
        if end_date:
            end_datetime = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(MedicationLog.administered_at < end_datetime)
        
        # Filter by status
        if status_filter:
            if status_filter == 'late':
                query = query.filter(MedicationLog.administered_late == True)
            elif status_filter == 'early':
                query = query.filter(MedicationLog.administered_early == True)
            elif status_filter == 'skipped':
                query = query.filter(MedicationLog.dose_amount == 0)
            elif status_filter == 'missed':
                # For missed doses, we need to check for scheduled times without corresponding logs
                # This is more complex and might need a different approach
                pass
            elif status_filter == 'on-time':
                query = query.filter(
                    MedicationLog.administered_late == False,
                    MedicationLog.administered_early == False,
                    MedicationLog.is_scheduled == True,
                    MedicationLog.dose_amount > 0
                )
        
        # Order by most recent first and apply limit
        records = query.order_by(MedicationLog.administered_at.desc()).limit(limit).all()
        
        # Format the results
        result = []
        for log in records:
            # Determine status
            if log.dose_amount == 0:
                status = 'skipped'
            elif log.is_scheduled and log.scheduled_time:
                # Calculate status based on actual time difference for more accurate results
                # Make both times timezone-naive for comparison
                administered_at = log.administered_at
                scheduled_time = log.scheduled_time
                
                if administered_at.tzinfo is not None:
                    administered_at = administered_at.replace(tzinfo=None)
                if scheduled_time.tzinfo is not None:
                    scheduled_time = scheduled_time.replace(tzinfo=None)
                
                time_diff_minutes = (administered_at - scheduled_time).total_seconds() / 60
                
                if time_diff_minutes < -60:  # More than 60 minutes early
                    status = 'early'
                elif time_diff_minutes > 60:  # More than 60 minutes late
                    status = 'late'
                else:  # Within 60 minutes
                    status = 'on-time'
            elif log.is_scheduled:
                # Fallback to database flags if no scheduled_time
                if log.administered_late:
                    status = 'late'
                elif log.administered_early:
                    status = 'early'
                else:
                    status = 'on-time'
            else:
                status = 'as-needed'
            
            # Calculate time difference for scheduled medications
            time_difference = None
            if log.scheduled_time and log.administered_at:
                diff_minutes = (log.administered_at - log.scheduled_time).total_seconds() / 60
                time_difference = f"{int(abs(diff_minutes))} minutes {'late' if diff_minutes > 0 else 'early'}" if diff_minutes != 0 else "on time"
            
            record = {
                'id': log.id,
                'medication_id': log.medication_id,
                'medication_name': log.medication.name,
                'dose_amount': log.dose_amount,
                'dose_unit': log.medication.quantity_unit,
                'administered_at': log.administered_at.isoformat(),
                'scheduled_time': log.scheduled_time.isoformat() if log.scheduled_time else None,
                'is_scheduled': log.is_scheduled,
                'status': status,
                'time_difference': time_difference,
                'notes': log.notes,
                'administered_by': log.administered_by,
                'created_at': log.created_at.isoformat()
            }
            result.append(record)
        
        return result
    
    except Exception as e:
        logger.error(f"Error getting medication history: {e}")
        return []

def get_medication_names_for_dropdown(db: Session):
    """
    Get all medication names for dropdown selection
    Returns active medications first, then inactive ones with indicators
    """
    try:
        from datetime import datetime
        today = datetime.now().date()
        
        # Get all medications ordered by active status (active first) then by name
        medications = db.query(Medication).filter(
            # Include all medications that exist in the system
            Medication.id.isnot(None)
        ).order_by(
            Medication.active.desc(),  # Active first
            Medication.name.asc()       # Then alphabetical
        ).all()
        
        result = []
        for med in medications:
            # Check if medication is truly active (active=True and not past end_date)
            is_active = med.active and (med.end_date is None or med.end_date > today)
            
            result.append({
                'id': med.id,
                'name': med.name,
                'display_name': f"{med.name}" + ("" if is_active else " (Inactive)"),
                'active': is_active
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting medication names for dropdown: {e}")
        return []
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
                timestamp=data_point['timestamp'],
                spo2=data_point['spo2'],
                bpm=data_point['bpm'],
                pa=data_point.get('perfusion'),
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
                'spo2_distribution': {},
                'avg_spo2': None,
                'min_spo2': None,
                'max_spo2': None,
                'avg_bpm': None,
                'min_bpm': None,
                'max_bpm': None
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
            'high_90s_97_plus': 0,     # 97+
            'mid_90s_94_96': 0,        # 94-96
            'low_90s_90_93': 0,        # 90-93
            'high_eighties_85_89': 0,  # 85-89
            'low_eighties_80_84': 0,   # 80-84
            'seventies_70_79': 0,      # 70-79
            'sixties_60_69': 0,        # 60-69
            'fifties_50_59': 0,        # 50-59
            'forties_40_49': 0,        # 40-49
            'thirties_30_39': 0,       # 30-39
            'twenties_20_29': 0,       # 20-29
            'below_twenty': 0,         # <20 but >0
            'zero_errors': 0           # 0 (errors)
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
                spo2_distribution['below_twenty'] += 1  # Values below 20 but >0
        
        # Count zero/error readings separately
        spo2_distribution['zero_errors'] = len(zero_spo2_readings)
        
        # Convert counts to percentages
        total_all_readings = len(valid_spo2_readings) + len(zero_spo2_readings)
        if total_all_readings > 0:
            for key in spo2_distribution:
                spo2_distribution[key] = {
                    'count': spo2_distribution[key],
                    'percentage': round((spo2_distribution[key] / total_all_readings) * 100, 2)
                }
        
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
        };
        
        return result;
        
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

# --- CareTask CRUD ---

def add_care_task(db: Session, name, description=None, category_id=None, active=True):
    """
    Add a new care task to the database.
    """
    from datetime import datetime
    now = datetime.now()
    care_task = CareTask(
        name=name,
        description=description,
        category_id=category_id,
        active=active,
        created_at=now,
        updated_at=now
    )
    db.add(care_task)
    db.commit()
    db.refresh(care_task)
    logger.info(f"Care task added: {name}")
    return care_task.id

def get_active_care_tasks(db: Session):
    """
    Get all active care tasks with their categories
    """
    try:
        care_tasks = db.query(CareTask).filter(CareTask.active == True).order_by(CareTask.name).all()
        
        result = []
        for task in care_tasks:
            # Get schedules for this task
            schedules = get_care_task_schedules(db, task.id)
            
            # Get category information
            category_info = None
            if task.category_id:
                category = db.query(CareTaskCategory).filter(CareTaskCategory.id == task.category_id).first()
                if category:
                    category_info = {
                        'id': category.id,
                        'name': category.name,
                        'description': category.description
                    }
            
            result.append({
                'id': task.id,
                'name': task.name,
                'description': task.description,
                'category_id': task.category_id,
                'category': category_info,
                'active': task.active,
                'created_at': task.created_at,
                'updated_at': task.updated_at,
                'schedules': schedules
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting active care tasks: {e}")
        return []

def get_inactive_care_tasks(db: Session):
    """
    Get all inactive care tasks with their categories
    """
    try:
        care_tasks = db.query(CareTask).filter(CareTask.active == False).order_by(CareTask.name).all()
        
        result = []
        for task in care_tasks:
            # Get schedules for this task
            schedules = get_care_task_schedules(db, task.id)
            
            # Get category information
            category_info = None
            if task.category_id:
                category = db.query(CareTaskCategory).filter(CareTaskCategory.id == task.category_id).first()
                if category:
                    category_info = {
                        'id': category.id,
                        'name': category.name,
                        'description': category.description
                    }
            
            result.append({
                'id': task.id,
                'name': task.name,
                'description': task.description,
                'category_id': task.category_id,
                'category': category_info,
                'active': task.active,
                'created_at': task.created_at,
                'updated_at': task.updated_at,
                'schedules': schedules
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting inactive care tasks: {e}")
        return []

def update_care_task(db: Session, task_id, **kwargs):
    """
    Update an existing care task
    """
    try:
        care_task = db.query(CareTask).filter(CareTask.id == task_id).first()
        if care_task:
            for key, value in kwargs.items():
                if hasattr(care_task, key):
                    setattr(care_task, key, value)
            care_task.updated_at = datetime.now()
            db.commit()
            logger.info(f"Care task {task_id} updated")
            return True
        return False
    except Exception as e:
        logger.error(f"Error updating care task {task_id}: {e}")
        db.rollback()
        return False

def delete_care_task(db: Session, task_id):
    """
    Delete a care task (soft delete by setting active=False)
    """
    try:
        care_task = db.query(CareTask).filter(CareTask.id == task_id).first()
        if care_task:
            care_task.active = False
            care_task.updated_at = datetime.now()
            db.commit()
            logger.info(f"Care task {task_id} deleted (soft delete)")
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting care task {task_id}: {e}")
        db.rollback()
        return False

# --- CareTaskSchedule CRUD ---

def add_care_task_schedule(db: Session, care_task_id, cron_expression, description=None, active=True, notes=None):
    """
    Add a new care task schedule
    """
    try:
        now = datetime.now()
        schedule = CareTaskSchedule(
            care_task_id=care_task_id,
            cron_expression=cron_expression,
            description=description,
            active=active,
            notes=notes,
            created_at=now,
            updated_at=now
        )
        db.add(schedule)
        db.commit()
        db.refresh(schedule)
        logger.info(f"Care task schedule added for task {care_task_id}: {cron_expression}")
        return schedule.id
    except Exception as e:
        logger.error(f"Error adding care task schedule: {e}")
        db.rollback()
        return None

def get_care_task_schedules(db: Session, care_task_id):
    """
    Get all schedules for a specific care task
    """
    try:
        schedules = db.query(CareTaskSchedule).filter(
            CareTaskSchedule.care_task_id == care_task_id
        ).order_by(CareTaskSchedule.created_at.desc()).all()
        
        return [
            {
                'id': s.id,
                'care_task_id': s.care_task_id,
                'cron_expression': s.cron_expression,
                'description': s.description,
                'active': s.active,
                'notes': s.notes,
                'created_at': s.created_at,
                'updated_at': s.updated_at
            } for s in schedules
        ]
        
    except Exception as e:
        logger.error(f"Error getting care task schedules: {e}")
        return []

def get_all_care_task_schedules(db: Session, active_only=True):
    """
    Get all care task schedules with care task details
    """
    try:
        query = db.query(CareTaskSchedule).join(CareTask)
        if active_only:
            query = query.filter(CareTaskSchedule.active == True, CareTask.active == True)
        
        schedules = query.order_by(CareTaskSchedule.created_at.desc()).all()
        
        return [
            {
                'id': s.id,
                'care_task_id': s.care_task_id,
                'care_task_name': s.care_task.name,
                'care_task_description': s.care_task.description,
                'care_task_group': s.care_task.group,
                'cron_expression': s.cron_expression,
                'description': s.description,
                'active': s.active,
                'notes': s.notes,
                'created_at': s.created_at,
                'updated_at': s.updated_at
            } for s in schedules
        ]
        
    except Exception as e:
        logger.error(f"Error getting all care task schedules: {e}")
        return []

def update_care_task_schedule(db: Session, schedule_id, **kwargs):
    """
    Update an existing care task schedule
    """
    try:
        schedule = db.query(CareTaskSchedule).filter(CareTaskSchedule.id == schedule_id).first()
        if schedule:
            for key, value in kwargs.items():
                if hasattr(schedule, key):
                    setattr(schedule, key, value)
            schedule.updated_at = datetime.now()
            db.commit()
            logger.info(f"Care task schedule {schedule_id} updated")
            return True
        return False
    except Exception as e:
        logger.error(f"Error updating care task schedule {schedule_id}: {e}")
        db.rollback()
        return False

def delete_care_task_schedule(db: Session, schedule_id):
    """
    Delete a care task schedule
    """
    try:
        schedule = db.query(CareTaskSchedule).filter(CareTaskSchedule.id == schedule_id).first()
        if schedule:
            db.delete(schedule)
            db.commit()
            logger.info(f"Care task schedule {schedule_id} deleted")
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting care task schedule {schedule_id}: {e}")
        db.rollback()
        return False

def toggle_care_task_schedule_active(db: Session, schedule_id):
    """
    Toggle the active status of a care task schedule
    """
    try:
        schedule = db.query(CareTaskSchedule).filter(CareTaskSchedule.id == schedule_id).first()
        if schedule:
            schedule.active = not schedule.active
            schedule.updated_at = datetime.now()
            db.commit()
            logger.info(f"Care task schedule {schedule_id} active status toggled to {schedule.active}")
            return schedule.active
        return None
    except Exception as e:
        logger.error(f"Error toggling care task schedule {schedule_id}: {e}")
        db.rollback()
        return None

def get_daily_care_task_schedule(db: Session):
    """
    Get today's care task schedule with timing information
    """
    try:
        from datetime import datetime, date
        from croniter import croniter
        
        # Get all active schedules
        schedules = get_all_care_task_schedules(db, active_only=True)
        
        today = date.today()
        scheduled_tasks = []
        
        for schedule in schedules:
            try:
                cron = croniter(schedule['cron_expression'], datetime.combine(today, datetime.min.time()))
                
                # Get all scheduled times for today
                scheduled_times = []
                current_time = datetime.combine(today, datetime.min.time())
                end_time = datetime.combine(today, datetime.max.time())
                
                while current_time <= end_time:
                    next_time = cron.get_next(datetime)
                    if next_time.date() == today:
                        scheduled_times.append(next_time)
                        current_time = next_time
                    else:
                        break
                
                for scheduled_time in scheduled_times:
                    scheduled_tasks.append({
                        'schedule_id': schedule['id'],
                        'care_task_id': schedule['care_task_id'],
                        'care_task_name': schedule['care_task_name'],
                        'care_task_description': schedule['care_task_description'],
                        'care_task_group': schedule['care_task_group'],
                        'scheduled_time': scheduled_time,
                        'cron_expression': schedule['cron_expression'],
                        'description': schedule['description'],
                        'notes': schedule['notes']
                    })
                    
            except Exception as e:
                logger.error(f"Error processing care task schedule {schedule['id']}: {e}")
                continue
        
        # Sort by scheduled time
        scheduled_tasks.sort(key=lambda x: x['scheduled_time'])
        
        return {'scheduled_care_tasks': scheduled_tasks}
        
    except Exception as e:
        logger.error(f"Error getting daily care task schedule: {e}")
        return {'scheduled_care_tasks': []}

def complete_care_task(db: Session, task_id, schedule_id=None, scheduled_time=None, notes=None, status='completed'):
    """
    Log completion of a care task
    """
    try:
        now = datetime.now()
        
        # Determine if this was scheduled and timing
        is_scheduled = schedule_id is not None
        completed_early = False
        completed_late = False
        
        if is_scheduled and scheduled_time:
            scheduled_dt = datetime.fromisoformat(scheduled_time.replace('Z', '+00:00')) if isinstance(scheduled_time, str) else scheduled_time
            time_diff = (now - scheduled_dt).total_seconds() / 60  # difference in minutes
            
            if time_diff < -5:  # More than 5 minutes early
                completed_early = True
            elif time_diff > 15:  # More than 15 minutes late
                completed_late = True
        
        care_task_log = CareTaskLog(
            care_task_id=task_id,
            schedule_id=schedule_id,
            completed_at=now,
            is_scheduled=is_scheduled,
            scheduled_time=scheduled_time,
            completed_early=completed_early,
            completed_late=completed_late,
            status=status,
            notes=notes,
            created_at=now
        )
        
        db.add(care_task_log)
        db.commit()
        db.refresh(care_task_log)
        
        logger.info(f"Care task {task_id} completed with status {status}")
        return care_task_log.id
        
    except Exception as e:
        logger.error(f"Error completing care task {task_id}: {e}")
        db.rollback()
        return None

def get_care_task_history(db: Session, limit=25, task_name=None, start_date=None, end_date=None, status_filter=None):
    """
    Get care task completion history with filtering options
    """
    try:
        query = db.query(CareTaskLog).join(CareTask)
        
        # Apply filters
        if task_name:
            query = query.filter(CareTask.name.ilike(f'%{task_name}%'))
        
        if start_date:
            start_dt = datetime.fromisoformat(start_date)
            query = query.filter(CareTaskLog.completed_at >= start_dt)
        
        if end_date:
            end_dt = datetime.fromisoformat(end_date)
            query = query.filter(CareTaskLog.completed_at <= end_dt)
        
        if status_filter and status_filter != 'all':
            query = query.filter(CareTaskLog.status == status_filter)
        
        logs = query.order_by(CareTaskLog.completed_at.desc()).limit(limit).all()
        
        return [
            {
                'id': log.id,
                'care_task_id': log.care_task_id,
                'care_task_name': log.care_task.name,
                'care_task_description': log.care_task.description,
                'care_task_group': log.care_task.group,
                'schedule_id': log.schedule_id,
                'completed_at': log.completed_at,
                'is_scheduled': log.is_scheduled,
                'scheduled_time': log.scheduled_time,
                'completed_early': log.completed_early,
                'completed_late': log.completed_late,
                'status': log.status,
                'notes': log.notes,
                'completed_by': log.completed_by,
                'created_at': log.created_at
            } for log in logs
        ]
        
    except Exception as e:
        logger.error(f"Error getting care task history: {e}")
        return []

def get_care_task_names_for_dropdown(db: Session):
    """
    Get distinct care task names for dropdown/autocomplete
    """
    try:
        names = db.query(CareTask.name).filter(CareTask.active == True).distinct().order_by(CareTask.name).all()
        return [name[0] for name in names]
    except Exception as e:
        logger.error(f"Error getting care task names: {e}")
        return []

# --- CareTaskCategory CRUD ---

def add_care_task_category(db: Session, name, description=None, color=None, is_default=False, active=True):
    """
    Add a new care task category to the database.
    """
    from datetime import datetime
    now = datetime.now()
    category = CareTaskCategory(
        name=name,
        description=description,
        color=color,
        is_default=is_default,
        active=active,
        created_at=now,
        updated_at=now
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    logger.info(f"Care task category added: {name}")
    return category.id

def get_care_task_categories(db: Session, active_only=True):
    """
    Get all care task categories
    """
    try:
        query = db.query(CareTaskCategory)
        if active_only:
            query = query.filter(CareTaskCategory.active == True)
        
        categories = query.order_by(CareTaskCategory.name).all()
        
        result = []
        for category in categories:
            result.append({
                'id': category.id,
                'name': category.name,
                'description': category.description,
                'color': category.color,
                'is_default': category.is_default,
                'active': category.active,
                'created_at': category.created_at,
                'updated_at': category.updated_at
            })
        
        return result
    except Exception as e:
        logger.error(f"Error getting care task categories: {e}")
        return []

def update_care_task_category(db: Session, category_id, **updates):
    """
    Update a care task category
    """
    try:
        from datetime import datetime
        category = db.query(CareTaskCategory).filter(CareTaskCategory.id == category_id).first()
        if not category:
            return False
        
        for key, value in updates.items():
            if hasattr(category, key):
                setattr(category, key, value)
        
        category.updated_at = datetime.now()
        db.commit()
        logger.info(f"Care task category {category_id} updated")
        return True
    except Exception as e:
        logger.error(f"Error updating care task category {category_id}: {e}")
        db.rollback()
        return False

def delete_care_task_category(db: Session, category_id):
    """
    Delete a care task category (only if not default and no tasks assigned)
    """
    try:
        category = db.query(CareTaskCategory).filter(CareTaskCategory.id == category_id).first()
        if not category:
            return False
        
        # Check if it's a default category
        if category.is_default:
            logger.warning(f"Cannot delete default category: {category.name}")
            return False
        
        # Check if any tasks are using this category
        task_count = db.query(CareTask).filter(CareTask.category_id == category_id).count()
        if task_count > 0:
            logger.warning(f"Cannot delete category {category.name}: {task_count} tasks still assigned")
            return False
        
        db.delete(category)
        db.commit()
        logger.info(f"Care task category {category.name} deleted")
        return True
    except Exception as e:
        logger.error(f"Error deleting care task category {category_id}: {e}")
        db.rollback()
        return False