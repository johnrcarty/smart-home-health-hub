import logging
import json
from datetime import datetime
from sqlalchemy.orm import Session
from .db import get_db
from .models import (BloodPressure, Temperature, Vital, Setting, PulseOxData,
    MonitoringAlert, Equipment, EquipmentChangeLog, VentilatorAlert, ExternalAlarm)

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
def save_vital(db: Session, vital_type, value, timestamp=None, notes=None):
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
        created_at=now
    )
    db.add(vital)
    db.commit()
    db.refresh(vital)
    logger.info(f"Vital saved: {vital_type}={value}")
    return vital.id

# --- Get Distinct Vital Types ---
def get_distinct_vital_types(db: Session):
    """
    Get a distinct list of vital_type values from the vitals table
    """
    types = db.query(Vital.vital_type).distinct().all()
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
                'notes': v.notes
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
                'notes': row.notes
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
            MonitoringAlert.acknowledged: 1
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
        count = db.query(MonitoringAlert).filter(MonitoringAlert.acknowledged == 0).count()
        return count
    except Exception as e:
        logger.error(f"Error getting unacknowledged alert count: {e}")
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
            query = query.filter(MonitoringAlert.acknowledged == 0)

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

def add_equipment(db: Session, name, last_changed, useful_days):
    try:
        equipment = Equipment(
            name=name,
            last_changed=last_changed,
            useful_days=useful_days
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
        # Calculate due date for each
        for item in equipment:
            from datetime import datetime, timedelta
            last = datetime.fromisoformat(item.last_changed)
            due = last + timedelta(days=item.useful_days)
            item.due_date = due.isoformat()
        # Sort by due_date
        equipment.sort(key=lambda x: x.due_date)
        return equipment
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
                acknowledged=0
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
            external_alarm_triggered=1,
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
        equipment = db.query(Equipment).all()
        from datetime import datetime, timedelta
        due_count = 0
        today = datetime.now().date()
        for item in equipment:
            last = datetime.fromisoformat(item.last_changed)
            due = last + timedelta(days=item.useful_days)
            if due.date() <= today:
                due_count += 1
        return due_count
    except Exception as e:
        logger.error(f"Error calculating equipment due count: {e}")
        return 0