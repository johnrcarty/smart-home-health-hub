from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, Boolean, DateTime
from sqlalchemy import TIMESTAMP
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class BloodPressure(Base):
    __tablename__ = 'blood_pressure'
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)
    systolic = Column(Integer, nullable=False)
    diastolic = Column(Integer, nullable=False)
    map = Column(Integer, nullable=False)
    raw_data = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False)

class Temperature(Base):
    __tablename__ = 'temperature'
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)
    skin_temp = Column(Float)
    body_temp = Column(Float)
    raw_data = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False)

class Vital(Base):
    __tablename__ = 'vitals'
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)
    vital_type = Column(String, nullable=False)
    vital_group = Column(String, nullable=True)  # New column for group/type
    value = Column(Float, nullable=False)
    notes = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False)

class Setting(Base):
    __tablename__ = 'settings'
    key = Column(String, primary_key=True)
    value = Column(Text, nullable=False)
    data_type = Column(String, nullable=False)
    description = Column(Text)
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False)

class PulseOxData(Base):
    __tablename__ = 'pulse_ox_data'
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)
    spo2 = Column(Integer)
    bpm = Column(Integer)
    pa = Column(Float)
    status = Column(String)
    motion = Column(String)
    spo2_alarm = Column(String)
    hr_alarm = Column(String)
    raw_data = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False)

class MonitoringAlert(Base):
    __tablename__ = 'monitoring_alerts'
    id = Column(Integer, primary_key=True, autoincrement=True)
    start_time = Column(TIMESTAMP(timezone=True), nullable=False)
    end_time = Column(TIMESTAMP(timezone=True))
    start_data_id = Column(Integer)
    end_data_id = Column(Integer)
    acknowledged = Column(Boolean, default=False)
    spo2_min = Column(Integer)
    bpm_min = Column(Integer)
    spo2_max = Column(Integer)
    bpm_max = Column(Integer)
    spo2_alarm_triggered = Column(Boolean, default=False)
    hr_alarm_triggered = Column(Boolean, default=False)
    external_alarm_triggered = Column(Boolean, default=False)
    oxygen_used = Column(Boolean, default=False)
    oxygen_highest = Column(Float)
    oxygen_unit = Column(String)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False)

class VentilatorAlert(Base):
    __tablename__ = 'ventilator_alerts'
    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String, nullable=False)
    pin = Column(Integer, nullable=False)
    start_time = Column(TIMESTAMP(timezone=True), nullable=False)
    end_time = Column(TIMESTAMP(timezone=True))
    last_activity = Column(TIMESTAMP(timezone=True), nullable=False)
    acknowledged = Column(Boolean, default=False)
    notes = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False)

class ExternalAlarm(Base):
    __tablename__ = 'external_alarms'
    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(Integer, ForeignKey('monitoring_alerts.id'))
    device_id = Column(String, nullable=False)
    pin = Column(Integer, nullable=False)
    start_time = Column(TIMESTAMP(timezone=True), nullable=False)
    end_time = Column(TIMESTAMP(timezone=True))
    last_activity = Column(TIMESTAMP(timezone=True), nullable=False)
    acknowledged = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False)
    monitoring_alert = relationship('MonitoringAlert', backref='external_alarms')

class Equipment(Base):
    __tablename__ = 'equipment'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    scheduled_replacement = Column(Boolean, nullable=False, default=True)
    last_changed = Column(TIMESTAMP(timezone=True), nullable=True)  # Nullable when scheduled_replacement is False
    useful_days = Column(Integer, nullable=True)  # Nullable when scheduled_replacement is False
    change_logs = relationship('EquipmentChangeLog', back_populates='equipment')

class EquipmentChangeLog(Base):
    __tablename__ = 'equipment_change_log'
    id = Column(Integer, primary_key=True, autoincrement=True)
    equipment_id = Column(Integer, ForeignKey('equipment.id'), nullable=False)
    changed_at = Column(TIMESTAMP(timezone=True), nullable=False)
    equipment = relationship('Equipment', back_populates='change_logs')

class Medication(Base):
    __tablename__ = 'medication'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    concentration = Column(String)
    quantity = Column(Float, nullable=False)
    quantity_unit = Column(String, nullable=False, default='tablets')
    instructions = Column(Text)
    start_date = Column(TIMESTAMP(timezone=True), nullable=True)
    end_date = Column(TIMESTAMP(timezone=True), nullable=True)
    as_needed = Column(Boolean, default=False)
    notes = Column(Text)
    active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False)
    
    # Relationships
    schedules = relationship('MedicationSchedule', back_populates='medication', cascade='all, delete-orphan')
    administration_logs = relationship('MedicationLog', back_populates='medication', cascade='all, delete-orphan')

class MedicationSchedule(Base):
    __tablename__ = 'medication_schedule'
    id = Column(Integer, primary_key=True, autoincrement=True)
    medication_id = Column(Integer, ForeignKey('medication.id'), nullable=False)
    
    # Cron expression for scheduling (e.g., "30 8 * * 1,3,5" for Mon/Wed/Fri at 8:30 AM)
    cron_expression = Column(String, nullable=False)
    
    # Human-readable description of the schedule (optional, for display purposes)
    description = Column(String, nullable=True)
    
    # Dose information for this specific schedule
    dose_amount = Column(Float, nullable=True)  # Amount per dose (e.g., 1, 0.5, 2) - unit inherited from medication
    
    # Active indicator - allows users to temporarily disable schedules
    active = Column(Boolean, default=True, nullable=False)
    
    # Optional notes for this specific schedule
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False)
    
    # Relationships
    medication = relationship('Medication', back_populates='schedules')
    administration_logs = relationship('MedicationLog', back_populates='schedule')

class MedicationLog(Base):
    __tablename__ = 'medication_log'
    id = Column(Integer, primary_key=True, autoincrement=True)
    medication_id = Column(Integer, ForeignKey('medication.id'), nullable=False)
    schedule_id = Column(Integer, ForeignKey('medication_schedule.id'), nullable=True)  # Null if administered without schedule
    
    # Administration details
    administered_at = Column(TIMESTAMP(timezone=True), nullable=False)
    dose_amount = Column(Float, nullable=False)  # Amount actually given - unit inherited from medication
    
    # Schedule tracking (only relevant if schedule_id is not null)
    is_scheduled = Column(Boolean, default=False, nullable=False)  # True if this was a scheduled dose
    scheduled_time = Column(TIMESTAMP(timezone=True), nullable=True)  # The originally scheduled time for this dose
    administered_early = Column(Boolean, default=False, nullable=False)  # True if given before scheduled time
    administered_late = Column(Boolean, default=False, nullable=False)   # True if given after scheduled time
    
    # Optional details
    notes = Column(Text, nullable=True)  # Any notes about this administration
    administered_by = Column(String, nullable=True)  # Who administered it (optional)
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), nullable=False)
    
    # Relationships
    medication = relationship('Medication', back_populates='administration_logs')
    schedule = relationship('MedicationSchedule', back_populates='administration_logs')

class CareTaskCategory(Base):
    __tablename__ = 'care_task_category'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=True)
    color = Column(String, nullable=True)  # Hex color code for category display
    is_default = Column(Boolean, default=False, nullable=False)  # True for non-deletable default categories
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False)
    
    # Relationships
    care_tasks = relationship('CareTask', back_populates='category')

class CareTask(Base):
    __tablename__ = 'care_task'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    category_id = Column(Integer, ForeignKey('care_task_category.id'), nullable=True)  # Reference to category
    active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False)
    
    # Relationships
    category = relationship('CareTaskCategory', back_populates='care_tasks')
    schedules = relationship('CareTaskSchedule', back_populates='care_task', cascade='all, delete-orphan')
    completion_logs = relationship('CareTaskLog', back_populates='care_task', cascade='all, delete-orphan')

class CareTaskSchedule(Base):
    __tablename__ = 'care_task_schedule'
    id = Column(Integer, primary_key=True, autoincrement=True)
    care_task_id = Column(Integer, ForeignKey('care_task.id'), nullable=False)
    
    # Cron expression for scheduling (e.g., "30 8 * * 1,3,5" for Mon/Wed/Fri at 8:30 AM)
    cron_expression = Column(String, nullable=False)
    
    # Human-readable description of the schedule (optional, for display purposes)
    description = Column(String, nullable=True)
    
    # Active indicator - allows users to temporarily disable schedules
    active = Column(Boolean, default=True, nullable=False)
    
    # Optional notes for this specific schedule
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False)
    
    # Relationships
    care_task = relationship('CareTask', back_populates='schedules')
    completion_logs = relationship('CareTaskLog', back_populates='schedule')

class CareTaskLog(Base):
    __tablename__ = 'care_task_log'
    id = Column(Integer, primary_key=True, autoincrement=True)
    care_task_id = Column(Integer, ForeignKey('care_task.id'), nullable=False)
    schedule_id = Column(Integer, ForeignKey('care_task_schedule.id'), nullable=True)  # Null if completed without schedule
    
    # Completion details
    completed_at = Column(TIMESTAMP(timezone=True), nullable=False)
    
    # Schedule tracking (only relevant if schedule_id is not null)
    is_scheduled = Column(Boolean, default=False, nullable=False)  # True if this was a scheduled task
    scheduled_time = Column(TIMESTAMP(timezone=True), nullable=True)  # The originally scheduled time for this task
    completed_early = Column(Boolean, default=False, nullable=False)  # True if completed before scheduled time
    completed_late = Column(Boolean, default=False, nullable=False)   # True if completed after scheduled time
    
    # Task completion status
    status = Column(String, default='completed', nullable=False)  # completed, skipped, partial
    
    # Optional details
    notes = Column(Text, nullable=True)  # Any notes about this completion
    completed_by = Column(String, nullable=True)  # Who completed it (optional)
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), nullable=False)
    
    # Relationships
    care_task = relationship('CareTask', back_populates='completion_logs')
    schedule = relationship('CareTaskSchedule', back_populates='completion_logs')
