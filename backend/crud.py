import logging
import json
from datetime import datetime, timedelta
from croniter import croniter
from sqlalchemy.orm import Session
from db import get_db
from models import (BloodPressure, Temperature, Vital, Setting, PulseOxData,
    MonitoringAlert, Equipment, EquipmentChangeLog, VentilatorAlert, ExternalAlarm, Medication, MedicationSchedule, MedicationLog)

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
                # For prior days, don't show completed medications - only show missed ones
                # Skip adding completed medications from yesterday to the list
                pass
            else:
                # Only show as missed if it's from yesterday or earlier
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
def administer_medication(db: Session, med_id, dose_amount, schedule_id=None, scheduled_time=None, notes=None):
    try:
        med = db.query(Medication).filter(Medication.id == med_id).first()
        if not med or med.quantity is None or dose_amount is None:
            return False
        # Deduct dose
        med.quantity = float(med.quantity) - float(dose_amount)
        # Record log
        from datetime import datetime
        log = MedicationLog(
            medication_id=med_id,
            schedule_id=schedule_id,
            administered_at=datetime.now(),
            dose_amount=dose_amount,
            is_scheduled=bool(schedule_id),
            scheduled_time=scheduled_time,
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
            elif status_filter == 'missed':
                # For missed doses, we need to check for scheduled times without corresponding logs
                # This is more complex and might need a different approach
                pass
            elif status_filter == 'on-time':
                query = query.filter(
                    MedicationLog.administered_late == False,
                    MedicationLog.administered_early == False,
                    MedicationLog.is_scheduled == True
                )
        
        # Order by most recent first and apply limit
        records = query.order_by(MedicationLog.administered_at.desc()).limit(limit).all()
        
        # Format the results
        result = []
        for log in records:
            # Determine status
            status = 'as-needed'
            if log.is_scheduled:
                if log.administered_late:
                    status = 'late'
                elif log.administered_early:
                    status = 'early'
                else:
                    status = 'on-time'
            
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