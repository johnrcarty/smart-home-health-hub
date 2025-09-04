"""
Equipment routes
"""
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from db import get_db
from crud.equipment import (
    get_equipment_list, log_equipment_change, receive_equipment, 
    open_equipment, get_equipment_change_history, get_equipment,
    get_equipment_categories, add_equipment, add_equipment_simple, add_equipment_category,
    update_equipment, update_equipment_category, delete_equipment,
    delete_equipment_category, search_equipment, get_equipment_due_count
)

logger = logging.getLogger("app")

router = APIRouter(prefix="/api/equipment", tags=["equipment"])


@router.post("")
async def api_add_equipment(data: dict = Body(...), db: Session = Depends(get_db)):
    """Add new equipment item."""
    name = data.get('name')
    quantity = data.get('quantity', 1)
    scheduled_replacement = data.get('scheduled_replacement', True)
    last_changed = data.get('last_changed')
    useful_days = data.get('useful_days')
    
    if not name:
        return JSONResponse(status_code=400, content={"detail": "Name is required"})
    
    if scheduled_replacement and (not last_changed or not useful_days):
        return JSONResponse(status_code=400, content={"detail": "Last changed and useful days are required for scheduled replacements"})
    
    eid = add_equipment_simple(db, name, quantity, scheduled_replacement, last_changed, useful_days)
    return {"id": eid, "status": "success"}


@router.get("")
async def api_get_equipment(db: Session = Depends(get_db)):
    """Get equipment list sorted by due next."""
    return get_equipment_list(db)


@router.post("/{equipment_id}/change")
async def api_log_equipment_change(equipment_id: int, data: dict = Body(...), db: Session = Depends(get_db)):
    """Log a change and update last_changed."""
    changed_at = data.get('changed_at')
    if not changed_at:
        return JSONResponse(status_code=400, content={"detail": "Missing changed_at"})
    
    # Check if equipment has scheduled replacement
    from models import Equipment
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        return JSONResponse(status_code=404, content={"detail": "Equipment not found"})
    
    if not equipment.scheduled_replacement:
        return JSONResponse(status_code=400, content={"detail": "Equipment does not have scheduled replacement"})
    
    success = log_equipment_change(db, equipment_id, changed_at)
    return {"success": success}


@router.get("/{equipment_id}/history")
async def api_get_equipment_history(equipment_id: int, db: Session = Depends(get_db)):
    """Get change history for equipment."""
    return get_equipment_change_history(db, equipment_id)


@router.post("/{equipment_id}/receive")
async def api_receive_equipment(equipment_id: int, data: dict = Body(...), db: Session = Depends(get_db)):
    """Increase equipment quantity (receive new stock)."""
    amount = data.get('amount', 1)
    success = receive_equipment(db, equipment_id, amount)
    return {"success": success}


@router.post("/{equipment_id}/open")
async def api_open_equipment(equipment_id: int, data: dict = Body(...), db: Session = Depends(get_db)):
    """Decrease equipment quantity (open/use equipment)."""
    amount = data.get('amount', 1)
    success = open_equipment(db, equipment_id, amount)
    return {"success": success}


@router.get("/due/count")
async def api_get_equipment_due_count(db: Session = Depends(get_db)):
    """Get count of equipment items that are due for replacement."""
    return {"count": get_equipment_due_count(db)}
