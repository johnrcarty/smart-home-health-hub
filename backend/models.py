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
    last_changed = Column(TIMESTAMP(timezone=True), nullable=False)
    useful_days = Column(Integer, nullable=False)
    change_logs = relationship('EquipmentChangeLog', back_populates='equipment')

class EquipmentChangeLog(Base):
    __tablename__ = 'equipment_change_log'
    id = Column(Integer, primary_key=True, autoincrement=True)
    equipment_id = Column(Integer, ForeignKey('equipment.id'), nullable=False)
    changed_at = Column(TIMESTAMP(timezone=True), nullable=False)
    equipment = relationship('Equipment', back_populates='change_logs')
