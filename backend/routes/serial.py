"""
Serial device communication routes
"""
import os
import logging
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from db import get_db
from crud import get_setting
from state_manager import get_serial_log, is_serial_mode

logger = logging.getLogger("app")

router = APIRouter(prefix="/api/serial", tags=["serial"])


@router.get("/log")
async def get_serial_log_endpoint():
    """Return the last raw serial lines for preview."""
    try:
        return {"lines": get_serial_log()}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/status")
async def get_serial_status(db: Session = Depends(get_db)):
    """Return serial reader status and configured baud rate."""
    try:
        configured_baud = get_setting(db, "baud_rate", os.getenv("BAUD_RATE", 19200))
        try:
            configured_baud = int(configured_baud)
        except Exception:
            pass
        return {
            "serial_active": is_serial_mode(),
            "baud_rate": configured_baud
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
