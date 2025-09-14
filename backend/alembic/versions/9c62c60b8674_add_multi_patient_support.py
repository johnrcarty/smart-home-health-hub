"""add_multi_patient_support

Revision ID: 9c62c60b8674
Revises: fc8f45c4e8dc
Create Date: 2025-09-09 16:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c62c60b8674'
down_revision: Union[str, None] = 'fc8f45c4e8dc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create patients table
    op.create_table('patients',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('first_name', sa.String(), nullable=False),
    sa.Column('last_name', sa.String(), nullable=False),
    sa.Column('date_of_birth', sa.DateTime(), nullable=True),
    sa.Column('medical_record_number', sa.String(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
    sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('medical_record_number')
    )
    
    # Create default patient for existing data
    op.execute("""
        INSERT INTO patients (id, first_name, last_name, date_of_birth, medical_record_number, is_active, notes, created_at, updated_at)
        VALUES (1, 'Patient1', '', '1900-01-01', 'DEFAULT001', true, 'Default patient created during migration', NOW(), NOW())
    """)
    
    # Add patient_id columns (nullable first, then update, then make non-nullable where needed)
    op.add_column('blood_pressure', sa.Column('patient_id', sa.Integer(), nullable=True))
    op.add_column('care_task', sa.Column('patient_id', sa.Integer(), nullable=True))
    op.add_column('care_task_log', sa.Column('patient_id', sa.Integer(), nullable=True))
    op.add_column('care_task_schedule', sa.Column('patient_id', sa.Integer(), nullable=True))
    op.add_column('equipment', sa.Column('patient_id', sa.Integer(), nullable=True))
    op.add_column('equipment', sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column('equipment', sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column('equipment_change_log', sa.Column('patient_id', sa.Integer(), nullable=True))
    op.add_column('equipment_change_log', sa.Column('notes', sa.Text(), nullable=True))
    op.add_column('equipment_change_log', sa.Column('changed_by', sa.String(), nullable=True))
    op.add_column('equipment_change_log', sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column('medication', sa.Column('patient_id', sa.Integer(), nullable=True))
    op.add_column('medication_log', sa.Column('patient_id', sa.Integer(), nullable=True))
    op.add_column('medication_schedule', sa.Column('patient_id', sa.Integer(), nullable=True))
    op.add_column('monitoring_alerts', sa.Column('patient_id', sa.Integer(), nullable=True))
    op.add_column('pulse_ox_data', sa.Column('patient_id', sa.Integer(), nullable=True))
    op.add_column('temperature', sa.Column('patient_id', sa.Integer(), nullable=True))
    op.add_column('ventilator_alerts', sa.Column('patient_id', sa.Integer(), nullable=True))
    op.add_column('vitals', sa.Column('patient_id', sa.Integer(), nullable=True))
    
    # Update existing records to use default patient (patient_id = 1)
    op.execute("UPDATE blood_pressure SET patient_id = 1 WHERE patient_id IS NULL")
    op.execute("UPDATE care_task_log SET patient_id = 1 WHERE patient_id IS NULL")
    op.execute("UPDATE medication_log SET patient_id = 1 WHERE patient_id IS NULL")
    op.execute("UPDATE monitoring_alerts SET patient_id = 1 WHERE patient_id IS NULL")
    op.execute("UPDATE pulse_ox_data SET patient_id = 1 WHERE patient_id IS NULL")
    op.execute("UPDATE temperature SET patient_id = 1 WHERE patient_id IS NULL")
    op.execute("UPDATE ventilator_alerts SET patient_id = 1 WHERE patient_id IS NULL")
    op.execute("UPDATE vitals SET patient_id = 1 WHERE patient_id IS NULL")
    
    # Update equipment timestamps
    op.execute("UPDATE equipment SET created_at = NOW(), updated_at = NOW() WHERE created_at IS NULL")
    op.execute("UPDATE equipment_change_log SET created_at = changed_at WHERE created_at IS NULL")
    
    # Make required columns non-nullable
    op.alter_column('blood_pressure', 'patient_id', nullable=False)
    op.alter_column('care_task_log', 'patient_id', nullable=False)  
    op.alter_column('medication_log', 'patient_id', nullable=False)
    op.alter_column('monitoring_alerts', 'patient_id', nullable=False)
    op.alter_column('pulse_ox_data', 'patient_id', nullable=False)
    op.alter_column('temperature', 'patient_id', nullable=False)
    op.alter_column('ventilator_alerts', 'patient_id', nullable=False)
    op.alter_column('vitals', 'patient_id', nullable=False)
    op.alter_column('equipment', 'created_at', nullable=False)
    op.alter_column('equipment', 'updated_at', nullable=False)
    op.alter_column('equipment_change_log', 'created_at', nullable=False)
    
    # Create foreign keys
    op.create_foreign_key(None, 'blood_pressure', 'patients', ['patient_id'], ['id'])
    op.create_foreign_key(None, 'care_task', 'patients', ['patient_id'], ['id'])
    op.create_foreign_key(None, 'care_task_log', 'patients', ['patient_id'], ['id'])
    op.create_foreign_key(None, 'care_task_schedule', 'patients', ['patient_id'], ['id'])
    op.create_foreign_key(None, 'equipment', 'patients', ['patient_id'], ['id'])
    op.create_foreign_key(None, 'equipment_change_log', 'patients', ['patient_id'], ['id'])
    op.create_foreign_key(None, 'medication', 'patients', ['patient_id'], ['id'])
    op.create_foreign_key(None, 'medication_log', 'patients', ['patient_id'], ['id'])
    op.create_foreign_key(None, 'medication_schedule', 'patients', ['patient_id'], ['id'])
    op.create_foreign_key(None, 'monitoring_alerts', 'patients', ['patient_id'], ['id'])
    op.create_foreign_key(None, 'pulse_ox_data', 'patients', ['patient_id'], ['id'])
    op.create_foreign_key(None, 'temperature', 'patients', ['patient_id'], ['id'])
    op.create_foreign_key(None, 'ventilator_alerts', 'patients', ['patient_id'], ['id'])
    op.create_foreign_key(None, 'vitals', 'patients', ['patient_id'], ['id'])


def downgrade() -> None:
    # Drop foreign keys
    op.drop_constraint(None, 'vitals', type_='foreignkey')
    op.drop_constraint(None, 'ventilator_alerts', type_='foreignkey')
    op.drop_constraint(None, 'temperature', type_='foreignkey')
    op.drop_constraint(None, 'pulse_ox_data', type_='foreignkey')
    op.drop_constraint(None, 'monitoring_alerts', type_='foreignkey')
    op.drop_constraint(None, 'medication_schedule', type_='foreignkey')
    op.drop_constraint(None, 'medication_log', type_='foreignkey')
    op.drop_constraint(None, 'medication', type_='foreignkey')
    op.drop_constraint(None, 'equipment_change_log', type_='foreignkey')
    op.drop_constraint(None, 'equipment', type_='foreignkey')
    op.drop_constraint(None, 'care_task_schedule', type_='foreignkey')
    op.drop_constraint(None, 'care_task_log', type_='foreignkey')
    op.drop_constraint(None, 'care_task', type_='foreignkey')
    op.drop_constraint(None, 'blood_pressure', type_='foreignkey')
    
    # Drop columns
    op.drop_column('vitals', 'patient_id')
    op.drop_column('ventilator_alerts', 'patient_id')
    op.drop_column('temperature', 'patient_id')
    op.drop_column('pulse_ox_data', 'patient_id')
    op.drop_column('monitoring_alerts', 'patient_id')
    op.drop_column('medication_schedule', 'patient_id')
    op.drop_column('medication_log', 'patient_id')
    op.drop_column('medication', 'patient_id')
    op.drop_column('equipment_change_log', 'created_at')
    op.drop_column('equipment_change_log', 'changed_by')
    op.drop_column('equipment_change_log', 'notes')
    op.drop_column('equipment_change_log', 'patient_id')
    op.drop_column('equipment', 'updated_at')
    op.drop_column('equipment', 'created_at')
    op.drop_column('equipment', 'patient_id')
    op.drop_column('care_task_schedule', 'patient_id')
    op.drop_column('care_task_log', 'patient_id')
    op.drop_column('care_task', 'patient_id')
    op.drop_column('blood_pressure', 'patient_id')
    
    # Drop patients table
    op.drop_table('patients')
