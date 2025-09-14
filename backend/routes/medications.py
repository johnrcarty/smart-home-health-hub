"""
Medication management routes
"""
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, Body
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
from db import get_db
from crud.medications import (add_medication, get_active_medications, get_inactive_medications, update_medication, 
                  delete_medication, add_medication_schedule, get_medication_schedules, 
                  get_all_medication_schedules, update_medication_schedule, delete_medication_schedule, 
                  toggle_medication_schedule_active, get_daily_medication_schedule, administer_medication,
                  get_medication_history, get_medication_names_for_dropdown)
from crud.settings import get_setting
from models import Medication

logger = logging.getLogger("app")

router = APIRouter(prefix="/api", tags=["medications"])


# Medication CRUD endpoints
@router.post("/add/medication")
async def api_add_medication(data: dict = Body(...), db: Session = Depends(get_db)):
    """Add a new medication entry."""
    required_fields = ["name", "concentration", "quantity", "quantity_unit", "instructions", "start_date", "as_needed", "notes"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return JSONResponse(status_code=400, content={"detail": f"Missing fields: {', '.join(missing)}"})

    # Extract fields
    name = data["name"]
    concentration = data["concentration"]
    quantity = data["quantity"]
    quantity_unit = data["quantity_unit"]
    instructions = data["instructions"]
    start_date = data["start_date"]
    as_needed = data["as_needed"]
    notes = data["notes"]
    end_date = data.get("end_date")  # Optional, not required in add form
    is_patient_specific = data.get("is_patient_specific", False)  # New field
    admin_patient_id = data.get("admin_patient_id")  # Admin can specify patient directly
    
    # Determine patient_id
    patient_id = None
    if is_patient_specific:
        if admin_patient_id:
            # Admin specified a specific patient
            patient_id = admin_patient_id
        else:
            # Use current patient from settings
            current_patient_id = get_setting(db, 'current_patient_id')
            if current_patient_id:
                try:
                    patient_id = int(current_patient_id)
                except (ValueError, TypeError):
                    return JSONResponse(status_code=400, content={"detail": "Invalid current patient ID"})
            else:
                return JSONResponse(status_code=400, content={"detail": "No current patient set for patient-specific medication"})

    try:
        med_id = add_medication(
            db,
            name=name,
            concentration=concentration,
            quantity=quantity,
            quantity_unit=quantity_unit,
            instructions=instructions,
            start_date=start_date,
            end_date=end_date,
            as_needed=as_needed,
            notes=notes,
            patient_id=patient_id
        )
        return {"id": med_id, "status": "success"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})


@router.get("/medications/active")
async def get_active_medications_endpoint(db: Session = Depends(get_db)):
    """Get all active medications."""
    return get_active_medications(db)


@router.get("/medications/inactive")
async def get_inactive_medications_endpoint(db: Session = Depends(get_db)):
    """Get all inactive medications."""
    return get_inactive_medications(db)


# Admin-specific endpoints with patient filtering
@router.get("/admin/medications/active")
async def get_admin_active_medications_endpoint(patient_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get active medications for admin view - can filter by patient_id or show all"""
    try:
        if patient_id:
            # Get medications for specific patient + global medications
            medications = db.query(Medication).filter(
                Medication.active == True,
                (Medication.end_date == None) | (Medication.end_date > datetime.now().date()),
                (Medication.patient_id == patient_id) | (Medication.patient_id == None)
            ).order_by(Medication.name).all()
        else:
            # Get all active medications (admin overview)
            medications = db.query(Medication).filter(
                Medication.active == True,
                (Medication.end_date == None) | (Medication.end_date > datetime.now().date())
            ).order_by(Medication.name).all()
        
        return [
            {
                'id': med.id,
                'patient_id': med.patient_id,
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
                'is_global': med.patient_id is None,
                'schedules': get_medication_schedules(db, med.id)
            }
            for med in medications
        ]
    except Exception as e:
        logger.error(f"Error fetching admin active medications: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)})


@router.get("/admin/medications/inactive")
async def get_admin_inactive_medications_endpoint(patient_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get inactive medications for admin view - can filter by patient_id or show all"""
    try:
        today = datetime.now().date()
        
        if patient_id:
            # Get medications for specific patient + global medications
            medications = db.query(Medication).filter(
                (Medication.active == False) | (Medication.end_date <= today),
                (Medication.patient_id == patient_id) | (Medication.patient_id == None)
            ).order_by(Medication.name).all()
        else:
            # Get all inactive medications (admin overview)
            medications = db.query(Medication).filter(
                (Medication.active == False) | (Medication.end_date <= today)
            ).order_by(Medication.name).all()
        
        return [
            {
                'id': med.id,
                'patient_id': med.patient_id,
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
                'is_global': med.patient_id is None,
                'schedules': get_medication_schedules(db, med.id)
            }
            for med in medications
        ]
    except Exception as e:
        logger.error(f"Error fetching admin inactive medications: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)})


@router.put("/medications/{med_id}")
async def update_medication_endpoint(med_id: int, data: dict = Body(...), db: Session = Depends(get_db)):
    """Update an existing medication."""
    # Remove id from data if present
    data.pop('id', None)
    
    success = update_medication(db, med_id, **data)
    if not success:
        return JSONResponse(status_code=404, content={"detail": "Medication not found"})
    
    return {"status": "success"}


@router.delete("/medications/{med_id}")
async def delete_medication_endpoint(med_id: int, db: Session = Depends(get_db)):
    """Delete (soft delete) a medication."""
    success = delete_medication(db, med_id)
    if not success:
        return JSONResponse(status_code=404, content={"detail": "Medication not found"})
    
    return {"status": "success"}


@router.post("/medications/{med_id}/toggle-active")
async def toggle_medication_active_endpoint(med_id: int, db: Session = Depends(get_db)):
    """Toggle the active status of a medication."""
    # Get current medication
    medication = db.query(Medication).filter(Medication.id == med_id).first()
    if not medication:
        return JSONResponse(status_code=404, content={"detail": "Medication not found"})
    
    # Toggle active status
    success = update_medication(db, med_id, active=not medication.active)
    if not success:
        return JSONResponse(status_code=500, content={"detail": "Failed to update medication"})
    
    return {"status": "success", "active": not medication.active}


@router.post("/medications/{med_id}/administer")
async def administer_medication_endpoint(med_id: int, data: dict = Body(...), db: Session = Depends(get_db)):
    """Record a medication administration and deduct from quantity."""
    dose_amount = data.get('dose_amount')
    schedule_id = data.get('schedule_id')
    scheduled_time = data.get('scheduled_time')
    notes = data.get('notes')
    result = administer_medication(db, med_id, dose_amount, schedule_id, scheduled_time, notes)
    if not result:
        return JSONResponse(status_code=400, content={"detail": "Failed to administer medication"})
    return {"success": True}


# Medication Schedule endpoints
@router.post("/add/schedule/{medication_id}")
async def api_add_medication_schedule(
    medication_id: int, 
    data: dict = Body(...), 
    db: Session = Depends(get_db)
):
    """Add a new medication schedule entry."""
    try:
        schedule_type = data.get('type', 'med')
        if schedule_type != 'med':
            return JSONResponse(status_code=400, content={"detail": "Invalid schedule type for medication"})
        
        # Validate required fields
        required_fields = ['cron_expression', 'description', 'dose_amount']
        for field in required_fields:
            if field not in data or not data[field]:
                return JSONResponse(status_code=400, content={"detail": f"Missing required field: {field}"})
        
        # Verify medication exists
        medication = db.query(Medication).filter(Medication.id == medication_id).first()
        if not medication:
            return JSONResponse(status_code=404, content={"detail": "Medication not found"})
        
        # For global medications, use provided patient_id; otherwise inherit from medication
        patient_id = None
        if medication.patient_id is None:  # Global medication
            patient_id = data.get('patient_id')
            if patient_id:
                patient_id = int(patient_id)
            else:
                # Fallback to current patient if no patient_id provided for global medication
                current_patient_id = get_setting(db, 'current_patient_id')
                if current_patient_id:
                    try:
                        patient_id = int(current_patient_id)
                    except (ValueError, TypeError):
                        pass  # Leave patient_id as None
        
        schedule_id = add_medication_schedule(
            db,
            medication_id=medication_id,
            cron_expression=data['cron_expression'],
            description=data['description'],
            dose_amount=data['dose_amount'],
            active=data.get('active', True),
            notes=data.get('notes', ''),
            patient_id=patient_id
        )
        
        if schedule_id:
            return {"id": schedule_id, "status": "success"}
        else:
            return JSONResponse(status_code=500, content={"detail": "Failed to create medication schedule"})
    
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"Internal server error: {str(e)}"})


@router.get("/medications/{medication_id}/schedules")
async def get_medication_schedules_endpoint(medication_id: int, db: Session = Depends(get_db)):
    """Get all schedules for a specific medication."""
    # Verify medication exists
    medication = db.query(Medication).filter(Medication.id == medication_id).first()
    if not medication:
        return JSONResponse(status_code=404, content={"detail": "Medication not found"})
    
    schedules = get_medication_schedules(db, medication_id)
    return {"schedules": schedules}


@router.get("/schedules")
async def get_all_medication_schedules_endpoint(active_only: bool = True, db: Session = Depends(get_db)):
    """Get all medication schedules, optionally filtering by active status."""
    schedules = get_all_medication_schedules(db, active_only)
    return {"schedules": schedules}


@router.put("/schedules/{schedule_id}")
async def update_medication_schedule_endpoint(
    schedule_id: int, 
    data: dict = Body(...), 
    db: Session = Depends(get_db)
):
    """Update an existing medication schedule."""
    # Remove id from data if present
    data.pop('id', None)
    
    success = update_medication_schedule(db, schedule_id, **data)
    if not success:
        return JSONResponse(status_code=404, content={"detail": "Medication schedule not found"})
    
    return {"status": "success"}


@router.delete("/schedules/{schedule_id}")
async def delete_medication_schedule_endpoint(schedule_id: int, db: Session = Depends(get_db)):
    """Delete a medication schedule."""
    success = delete_medication_schedule(db, schedule_id)
    if not success:
        return JSONResponse(status_code=404, content={"detail": "Medication schedule not found"})
    
    return {"status": "success"}


@router.post("/schedules/{schedule_id}/toggle-active")
async def toggle_medication_schedule_active_endpoint(schedule_id: int, db: Session = Depends(get_db)):
    """Toggle the active status of a medication schedule."""
    success, new_active_status = toggle_medication_schedule_active(db, schedule_id)
    if not success:
        return JSONResponse(status_code=404, content={"detail": "Medication schedule not found"})
    
    return {"status": "success", "active": new_active_status}


@router.get("/schedules/daily")
async def get_daily_medication_schedule_endpoint(db: Session = Depends(get_db)):
    """Get today's scheduled medications plus yesterday's missed medications."""
    try:
        daily_schedule = get_daily_medication_schedule(db)
        return daily_schedule
    except Exception as e:
        logger.error(f"Error getting daily medication schedule: {e}")
        return JSONResponse(
            status_code=500, 
            content={"detail": f"Error retrieving daily schedule: {str(e)}"}
        )


# Medication history and reporting
@router.get("/medications/history")
async def get_medication_history_endpoint(
    limit: int = 25,
    medication_name: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get medication administration history with filtering options
    
    Query parameters:
    - limit: Maximum number of records (default 25)
    - medication_name: Filter by medication name (partial match)
    - start_date: Filter by start date (YYYY-MM-DD format)
    - end_date: Filter by end date (YYYY-MM-DD format)
    - status_filter: Filter by status ('late', 'early', 'missed', 'on-time')
    """
    try:
        history = get_medication_history(
            db=db,
            limit=limit,
            medication_name=medication_name,
            start_date=start_date,
            end_date=end_date,
            status_filter=status_filter
        )
        return {"history": history, "count": len(history)}
    except Exception as e:
        logger.error(f"Error getting medication history: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error retrieving medication history: {str(e)}"}
        )


@router.get("/medications/names")
async def get_medication_names_endpoint(db: Session = Depends(get_db)):
    """
    Get all medication names for dropdown selection
    Returns active medications first, then inactive ones with indicators
    """
    try:
        medication_names = get_medication_names_for_dropdown(db)
        return {"medication_names": medication_names}
    except Exception as e:
        logger.error(f"Error getting medication names: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error retrieving medication names: {str(e)}"}
        )
