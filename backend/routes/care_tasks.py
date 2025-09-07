"""
Care task management routes
"""
import logging
from fastapi import APIRouter, Depends, Body
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from db import get_db
from crud.care_tasks import (
    add_care_task, get_care_tasks, get_care_task, update_care_task, 
    delete_care_task, toggle_care_task_active, log_care_task,
    add_care_task_category, get_care_task_categories, update_care_task_category, 
    delete_care_task_category, get_care_task_logs, get_recent_care_task_completions,
    get_care_task_completion_stats, get_overdue_care_tasks
)
from crud.scheduling import (
    add_care_task_schedule, get_care_task_schedules, get_all_care_task_schedules,
    update_care_task_schedule, delete_care_task_schedule, toggle_care_task_schedule_active,
    get_daily_care_task_schedule, complete_care_task, get_care_task_schedule,
    validate_cron_expression, get_next_scheduled_times
)

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
        care_tasks = get_care_tasks(db, active_only=True)
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
        care_tasks = get_care_tasks(db, active_only=False)
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
        success, new_active_status = toggle_care_task_active(db, task_id)
        
        if success:
            return {"status": "success", "active": new_active_status}
        else:
            return JSONResponse(status_code=404, content={"detail": "Care task not found"})
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
        log_id = log_care_task(
            db=db,
            task_id=task_id,
            completion_status=data.get("status", "completed"),
            notes=data.get("notes"),
            completed_by=data.get("completed_by")
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
        # Validate cron expression first
        cron_expression = data.get("cron_expression")
        if not cron_expression:
            return JSONResponse(status_code=400, content={"detail": "cron_expression is required"})
        
        is_valid, error_msg = validate_cron_expression(cron_expression)
        if not is_valid:
            return JSONResponse(status_code=400, content={"detail": f"Invalid cron expression: {error_msg}"})
        
        schedule_id = add_care_task_schedule(
            db=db,
            care_task_id=care_task_id,
            cron_expression=cron_expression,
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


@router.get("/care-task-schedules/{schedule_id}")
async def get_care_task_schedule_endpoint(schedule_id: int, db: Session = Depends(get_db)):
    """Get a specific care task schedule"""
    try:
        schedule = get_care_task_schedule(db, schedule_id)
        if schedule:
            return {"schedule": schedule}
        else:
            return JSONResponse(status_code=404, content={"detail": "Care task schedule not found"})
    except Exception as e:
        logger.error(f"Error getting care task schedule {schedule_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error retrieving care task schedule: {str(e)}"}
        )


@router.put("/care-task-schedules/{schedule_id}")
async def update_care_task_schedule_endpoint(schedule_id: int, data: dict = Body(...), db: Session = Depends(get_db)):
    """Update an existing care task schedule"""
    try:
        # Validate cron expression if provided
        if "cron_expression" in data:
            is_valid, error_msg = validate_cron_expression(data["cron_expression"])
            if not is_valid:
                return JSONResponse(status_code=400, content={"detail": f"Invalid cron expression: {error_msg}"})
        
        success = update_care_task_schedule(db, schedule_id, **data)
        if success:
            return {"status": "success"}
        else:
            return JSONResponse(status_code=404, content={"detail": "Care task schedule not found"})
    except Exception as e:
        logger.error(f"Error updating care task schedule {schedule_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error updating care task schedule: {str(e)}"}
        )


@router.delete("/care-task-schedules/{schedule_id}")
async def delete_care_task_schedule_endpoint(schedule_id: int, db: Session = Depends(get_db)):
    """Delete a care task schedule"""
    try:
        success = delete_care_task_schedule(db, schedule_id)
        if success:
            return {"status": "success"}
        else:
            return JSONResponse(status_code=404, content={"detail": "Care task schedule not found"})
    except Exception as e:
        logger.error(f"Error deleting care task schedule {schedule_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error deleting care task schedule: {str(e)}"}
        )


@router.post("/care-task-schedules/{schedule_id}/toggle-active")
async def toggle_care_task_schedule_active_endpoint(schedule_id: int, db: Session = Depends(get_db)):
    """Toggle active status of a care task schedule"""
    try:
        success, new_active_status = toggle_care_task_schedule_active(db, schedule_id)
        if success:
            return {"status": "success", "active": new_active_status}
        else:
            return JSONResponse(status_code=404, content={"detail": "Care task schedule not found"})
    except Exception as e:
        logger.error(f"Error toggling care task schedule {schedule_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error toggling care task schedule status: {str(e)}"}
        )


@router.post("/care-task-schedule/{schedule_id}/complete")
async def complete_care_task_schedule_endpoint(schedule_id: int, data: dict = Body(...), db: Session = Depends(get_db)):
    """Complete a scheduled care task"""
    try:
        # Get the schedule to find the care task ID
        schedule = get_care_task_schedule(db, schedule_id)
        if not schedule:
            return JSONResponse(status_code=404, content={"detail": "Care task schedule not found"})
        
        log_id = complete_care_task(
            db=db,
            task_id=schedule['care_task_id'],
            schedule_id=schedule_id,
            scheduled_time=data.get("scheduled_time"),
            notes=data.get("notes"),
            status="completed",
            completed_by=data.get("completed_by")
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
        schedule = get_care_task_schedule(db, schedule_id)
        if not schedule:
            return JSONResponse(status_code=404, content={"detail": "Care task schedule not found"})
        
        log_id = complete_care_task(
            db=db,
            task_id=schedule['care_task_id'],
            schedule_id=schedule_id,
            scheduled_time=data.get("scheduled_time"),
            notes=data.get("notes", "Task skipped"),
            status="skipped",
            completed_by=data.get("completed_by")
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
            color=data.get("color", "#3B82F6")
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
async def get_care_task_categories_endpoint(db: Session = Depends(get_db)):
    """Get all care task categories"""
    try:
        categories = get_care_task_categories(db)
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


# Additional endpoints using new CRUD functions
@router.get("/care-tasks/{task_id}")
async def get_care_task_endpoint(task_id: int, db: Session = Depends(get_db)):
    """Get a specific care task by ID"""
    try:
        task = get_care_task(db, task_id)
        if task:
            return {"care_task": task}
        else:
            return JSONResponse(status_code=404, content={"detail": "Care task not found"})
    except Exception as e:
        logger.error(f"Error getting care task {task_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error retrieving care task: {str(e)}"}
        )


@router.get("/care-tasks/logs")
async def get_care_task_logs_endpoint(
    task_id: int = None, 
    limit: int = 50, 
    start_date: str = None, 
    end_date: str = None, 
    db: Session = Depends(get_db)
):
    """Get care task completion logs with optional filtering"""
    try:
        logs = get_care_task_logs(db, task_id, limit, start_date, end_date)
        return {"logs": logs}
    except Exception as e:
        logger.error(f"Error getting care task logs: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error retrieving care task logs: {str(e)}"}
        )


@router.get("/care-tasks/completions/recent")
async def get_recent_completions_endpoint(days: int = 7, db: Session = Depends(get_db)):
    """Get recent care task completions"""
    try:
        completions = get_recent_care_task_completions(db, days)
        return {"completions": completions}
    except Exception as e:
        logger.error(f"Error getting recent care task completions: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error retrieving recent completions: {str(e)}"}
        )


@router.get("/care-tasks/stats/completion")
async def get_completion_stats_endpoint(days: int = 30, db: Session = Depends(get_db)):
    """Get care task completion statistics"""
    try:
        stats = get_care_task_completion_stats(db, days)
        return {"stats": stats}
    except Exception as e:
        logger.error(f"Error getting care task completion stats: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error retrieving completion stats: {str(e)}"}
        )


@router.get("/care-tasks/overdue")
async def get_overdue_tasks_endpoint(db: Session = Depends(get_db)):
    """Get overdue care tasks"""
    try:
        overdue_tasks = get_overdue_care_tasks(db)
        return {"overdue_tasks": overdue_tasks}
    except Exception as e:
        logger.error(f"Error getting overdue care tasks: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error retrieving overdue tasks: {str(e)}"}
        )


# Additional scheduling utility endpoints
@router.post("/care-task-schedules/validate-cron")
async def validate_cron_expression_endpoint(data: dict = Body(...)):
    """Validate a cron expression"""
    try:
        cron_expression = data.get("cron_expression")
        if not cron_expression:
            return JSONResponse(status_code=400, content={"detail": "cron_expression is required"})
        
        is_valid, error_msg = validate_cron_expression(cron_expression)
        
        if is_valid:
            return {
                "valid": True,
                "message": "Cron expression is valid"
            }
        else:
            return {
                "valid": False,
                "error": error_msg
            }
    except Exception as e:
        logger.error(f"Error validating cron expression: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error validating cron expression: {str(e)}"}
        )


@router.get("/care-task-schedules/{schedule_id}/next-times")
async def get_next_scheduled_times_endpoint(schedule_id: int, count: int = 5, db: Session = Depends(get_db)):
    """Get the next N scheduled times for a specific schedule"""
    try:
        next_times = get_next_scheduled_times(db, schedule_id, count)
        return {
            "schedule_id": schedule_id,
            "next_times": [time.isoformat() for time in next_times],
            "count": len(next_times)
        }
    except Exception as e:
        logger.error(f"Error getting next scheduled times for schedule {schedule_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error getting next scheduled times: {str(e)}"}
        )
