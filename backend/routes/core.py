"""
Core application routes - basic endpoints, websockets, limits
"""
import os
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from db import get_db
from crud.vitals import get_latest_blood_pressure, get_blood_pressure_history, get_last_n_temperature
from state_manager import register_websocket_client, unregister_websocket_client, broadcast_state

logger = logging.getLogger("app")

router = APIRouter()

# Environment variables for limits
MIN_SPO2 = os.getenv("MIN_SPO2")
MAX_SPO2 = os.getenv("MAX_SPO2")
MIN_BPM = os.getenv("MIN_BPM")
MAX_BPM = os.getenv("MAX_BPM")


@router.websocket("/ws/sensors")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print(f"[core] WebSocket client connected: {websocket}")
    register_websocket_client(websocket)

    try:
        while True:
            # Just keep the connection alive
            data = await websocket.receive_text()
            # You can handle commands here if needed
    except WebSocketDisconnect:
        print(f"[core] WebSocket client disconnected: {websocket}")
        unregister_websocket_client(websocket)
    except Exception as e:
        print(f"[core] WebSocket error: {e}")
        unregister_websocket_client(websocket)


@router.get("/limits")
def get_limits():
    return {
        "spo2": {"min": MIN_SPO2, "max": MAX_SPO2},
        "bpm": {"min": MIN_BPM, "max": MAX_BPM}
    }


# Legacy blood pressure endpoints (keeping for backward compatibility)
@router.get("/blood-pressure/latest")
def latest_blood_pressure(db: Session = Depends(get_db)):
    return get_latest_blood_pressure(db) or {"message": "No data available"}


@router.get("/blood-pressure/history")
def blood_pressure_history(limit: int = 100, db: Session = Depends(get_db)):
    return get_blood_pressure_history(db, limit)


# Legacy temperature endpoints (keeping for backward compatibility)
@router.get("/temperature/latest")
def latest_temperature(db: Session = Depends(get_db)):
    temps = get_last_n_temperature(db, 1)
    return temps[0] if temps else {"message": "No data available"}


@router.get("/temperature/history")
def temperature_history(limit: int = 100, db: Session = Depends(get_db)):
    return get_last_n_temperature(db, limit)


# Test endpoint
@router.get("/api/test")
async def test_endpoint():
    return {"status": "success", "message": "API is working"}


# Dev endpoint to trigger websocket broadcast
@router.post("/api/dev/broadcast")
async def trigger_broadcast():
    """Trigger a websocket broadcast for development/testing purposes"""
    try:
        broadcast_state()
        return {"status": "success", "message": "Websocket broadcast triggered"}
    except Exception as e:
        logger.error(f"Error triggering broadcast: {e}")
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error triggering broadcast: {str(e)}"}
        )
