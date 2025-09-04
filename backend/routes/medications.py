"""
Medication management routes
"""
import logging
from fastapi import APIRouter, Depends, Body
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
from db import get_db
from crud import (add_medication, get_active_medications, get_inactive_medications, update_medication, 
                  delete_medication, add_medication_schedule, get_medication_schedules, 
                  get_all_medication_schedules, update_medication_schedule, delete_medication_schedule, 
                  toggle_medication_schedule_active, get_daily_medication_schedule, administer_medication,
                  get_medication_history, get_medication_names_for_dropdown)
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
            notes=notes
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
        
        schedule_id = add_medication_schedule(
            db,
            medication_id=medication_id,
            cron_expression=data['cron_expression'],
            description=data['description'],
            dose_amount=data['dose_amount'],
            active=data.get('active', True),
            notes=data.get('notes', '')
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
