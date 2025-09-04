"""
Care task management routes
"""
import logging
from fastapi import APIRouter, Depends, Body
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from db import get_db
from crud import (add_care_task, get_active_care_tasks, get_inactive_care_tasks, update_care_task, 
                  delete_care_task, add_care_task_schedule, get_care_task_schedules, 
                  get_all_care_task_schedules, update_care_task_schedule, delete_care_task_schedule, 
                  toggle_care_task_schedule_active, get_daily_care_task_schedule, complete_care_task,
                  add_care_task_category, get_care_task_categories, update_care_task_category, 
                  delete_care_task_category)
from models import CareTaskSchedule

logger = logging.getLogger("app")

router = APIRouter(prefix="/api", tags=["care_tasks"])


# Care Task CRUD endpoints
@router.post("/add/care-task")
async def api_add_care_task(data: dict = Body(...), db: Session = Depends(get_db)):
    """Add a new care task"""
    try:
        task_id = add_care_task(
            db=db,
            name=data.get("name"),
            description=data.get("description"),
            category_id=data.get("category_id"),
            active=data.get("active", True)
        )
        if task_id:
            return {"id": task_id, "status": "success"}
        else:
            return JSONResponse(status_code=500, content={"detail": "Failed to create care task"})
    except Exception as e:
        logger.error(f"Error adding care task: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error adding care task: {str(e)}"}
        )


@router.get("/care-tasks/active")
async def get_active_care_tasks_endpoint(db: Session = Depends(get_db)):
    """Get all active care tasks with their schedules"""
    try:
        care_tasks = get_active_care_tasks(db)
        return {"care_tasks": care_tasks}
    except Exception as e:
        logger.error(f"Error getting active care tasks: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error retrieving active care tasks: {str(e)}"}
        )


@router.get("/care-tasks/inactive")
async def get_inactive_care_tasks_endpoint(db: Session = Depends(get_db)):
    """Get all inactive care tasks with their schedules"""
    try:
        care_tasks = get_inactive_care_tasks(db)
        return {"care_tasks": care_tasks}
    except Exception as e:
        logger.error(f"Error getting inactive care tasks: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error retrieving inactive care tasks: {str(e)}"}
        )


@router.put("/care-tasks/{task_id}")
async def update_care_task_endpoint(task_id: int, data: dict = Body(...), db: Session = Depends(get_db)):
    """Update an existing care task"""
    try:
        success = update_care_task(db, task_id, **data)
        if success:
            return {"status": "success"}
        else:
            return JSONResponse(status_code=404, content={"detail": "Care task not found"})
    except Exception as e:
        logger.error(f"Error updating care task {task_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error updating care task: {str(e)}"}
        )


@router.delete("/care-tasks/{task_id}")
async def delete_care_task_endpoint(task_id: int, db: Session = Depends(get_db)):
    """Delete (deactivate) a care task"""
    try:
        success = delete_care_task(db, task_id)
        if success:
            return {"status": "success"}
        else:
            return JSONResponse(status_code=404, content={"detail": "Care task not found"})
    except Exception as e:
        logger.error(f"Error deleting care task {task_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error deleting care task: {str(e)}"}
        )


@router.post("/care-tasks/{task_id}/toggle-active")
async def toggle_care_task_active_endpoint(task_id: int, db: Session = Depends(get_db)):
    """Toggle active status of a care task"""
    try:
        # Get current task
        care_tasks = get_active_care_tasks(db) + get_inactive_care_tasks(db)
        task = next((t for t in care_tasks if t['id'] == task_id), None)
        
        if not task:
            return JSONResponse(status_code=404, content={"detail": "Care task not found"})
        
        # Toggle active status
        new_active_status = not task['active']
        success = update_care_task(db, task_id, active=new_active_status)
        
        if success:
            return {"status": "success", "active": new_active_status}
        else:
            return JSONResponse(status_code=500, content={"detail": "Failed to update care task"})
    except Exception as e:
        logger.error(f"Error toggling care task {task_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error toggling care task status: {str(e)}"}
        )


@router.post("/care-tasks/{task_id}/complete")
async def complete_care_task_endpoint(task_id: int, data: dict = Body(...), db: Session = Depends(get_db)):
    """Complete a care task"""
    try:
        log_id = complete_care_task(
            db=db,
            task_id=task_id,
            schedule_id=data.get("schedule_id"),
            scheduled_time=data.get("scheduled_time"),
            notes=data.get("notes"),
            status=data.get("status", "completed")
        )
        if log_id:
            return {"id": log_id, "status": "success"}
        else:
            return JSONResponse(status_code=500, content={"detail": "Failed to complete care task"})
    except Exception as e:
        logger.error(f"Error completing care task {task_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error completing care task: {str(e)}"}
        )


# Care Task Schedule endpoints
@router.post("/add/care-task-schedule/{care_task_id}")
async def api_add_care_task_schedule(
    care_task_id: int, 
    data: dict = Body(...), 
    db: Session = Depends(get_db)
):
    """Add a schedule to a care task"""
    try:
        schedule_id = add_care_task_schedule(
            db=db,
            care_task_id=care_task_id,
            cron_expression=data.get("cron_expression"),
            description=data.get("description"),
            active=data.get("active", True),
            notes=data.get("notes")
        )
        if schedule_id:
            return {"id": schedule_id, "status": "success"}
        else:
            return JSONResponse(status_code=500, content={"detail": "Failed to create care task schedule"})
    except Exception as e:
        logger.error(f"Error adding care task schedule: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error adding care task schedule: {str(e)}"}
        )


@router.get("/care-tasks/{care_task_id}/schedules")
async def get_care_task_schedules_endpoint(care_task_id: int, db: Session = Depends(get_db)):
    """Get all schedules for a specific care task"""
    try:
        schedules = get_care_task_schedules(db, care_task_id)
        return {"schedules": schedules}
    except Exception as e:
        logger.error(f"Error getting care task schedules: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error retrieving care task schedules: {str(e)}"}
        )


@router.get("/care-task-schedules")
async def get_all_care_task_schedules_endpoint(active_only: bool = True, db: Session = Depends(get_db)):
    """Get all care task schedules"""
    try:
        schedules = get_all_care_task_schedules(db, active_only)
        return {"schedules": schedules}
    except Exception as e:
        logger.error(f"Error getting all care task schedules: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error retrieving care task schedules: {str(e)}"}
        )


@router.get("/care-task-schedules/daily")
async def get_daily_care_task_schedule_endpoint(db: Session = Depends(get_db)):
    """Get today's care task schedule"""
    try:
        schedule = get_daily_care_task_schedule(db)
        return schedule
    except Exception as e:
        logger.error(f"Error getting daily care task schedule: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error retrieving daily care task schedule: {str(e)}"}
        )


@router.post("/care-task-schedule/{schedule_id}/complete")
async def complete_care_task_schedule_endpoint(schedule_id: int, data: dict = Body(...), db: Session = Depends(get_db)):
    """Complete a scheduled care task"""
    try:
        # Get the schedule to find the care task ID
        schedule = db.query(CareTaskSchedule).filter(CareTaskSchedule.id == schedule_id).first()
        if not schedule:
            return JSONResponse(status_code=404, content={"detail": "Care task schedule not found"})
        
        log_id = complete_care_task(
            db=db,
            task_id=schedule.care_task_id,
            schedule_id=schedule_id,
            scheduled_time=data.get("scheduled_time"),
            notes=data.get("notes"),
            status="completed"
        )
        if log_id:
            return {"id": log_id, "status": "success"}
        else:
            return JSONResponse(status_code=500, content={"detail": "Failed to complete care task"})
    except Exception as e:
        logger.error(f"Error completing care task schedule {schedule_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error completing care task: {str(e)}"}
        )


@router.post("/care-task-schedule/{schedule_id}/skip")
async def skip_care_task_schedule_endpoint(schedule_id: int, data: dict = Body(...), db: Session = Depends(get_db)):
    """Skip a scheduled care task"""
    try:
        # Get the schedule to find the care task ID
        schedule = db.query(CareTaskSchedule).filter(CareTaskSchedule.id == schedule_id).first()
        if not schedule:
            return JSONResponse(status_code=404, content={"detail": "Care task schedule not found"})
        
        log_id = complete_care_task(
            db=db,
            task_id=schedule.care_task_id,
            schedule_id=schedule_id,
            scheduled_time=data.get("scheduled_time"),
            notes=data.get("notes", "Task skipped"),
            status="skipped"
        )
        if log_id:
            return {"id": log_id, "status": "success"}
        else:
            return JSONResponse(status_code=500, content={"detail": "Failed to skip care task"})
    except Exception as e:
        logger.error(f"Error skipping care task schedule {schedule_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error skipping care task: {str(e)}"}
        )


# Care Task Category endpoints
@router.post("/add/care-task-category")
async def api_add_care_task_category(data: dict = Body(...), db: Session = Depends(get_db)):
    """Add a new care task category"""
    try:
        category_id = add_care_task_category(
            db=db,
            name=data.get("name"),
            description=data.get("description"),
            color=data.get("color"),
            is_default=data.get("is_default", False),
            active=data.get("active", True)
        )
        if category_id:
            return {"id": category_id, "status": "success"}
        else:
            return JSONResponse(status_code=500, content={"detail": "Failed to create care task category"})
    except Exception as e:
        logger.error(f"Error adding care task category: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error adding care task category: {str(e)}"}
        )


@router.get("/care-task-categories")
async def get_care_task_categories_endpoint(active_only: bool = True, db: Session = Depends(get_db)):
    """Get all care task categories"""
    try:
        categories = get_care_task_categories(db, active_only)
        return {"categories": categories}
    except Exception as e:
        logger.error(f"Error getting care task categories: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error retrieving care task categories: {str(e)}"}
        )


@router.put("/care-task-categories/{category_id}")
async def update_care_task_category_endpoint(category_id: int, data: dict = Body(...), db: Session = Depends(get_db)):
    """Update an existing care task category"""
    try:
        success = update_care_task_category(db, category_id, **data)
        if success:
            return {"status": "success"}
        else:
            return JSONResponse(status_code=404, content={"detail": "Care task category not found"})
    except Exception as e:
        logger.error(f"Error updating care task category {category_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error updating care task category: {str(e)}"}
        )


@router.delete("/care-task-categories/{category_id}")
async def delete_care_task_category_endpoint(category_id: int, db: Session = Depends(get_db)):
    """Delete a care task category (only if not default and no tasks assigned)"""
    try:
        success = delete_care_task_category(db, category_id)
        if success:
            return {"status": "success"}
        else:
            return JSONResponse(status_code=400, content={"detail": "Cannot delete default category or category with assigned tasks"})
    except Exception as e:
        logger.error(f"Error deleting care task category {category_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error deleting care task category: {str(e)}"}
        )
