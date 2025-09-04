"""
Settings management routes
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any
from db import get_db
from crud.settings import get_all_settings, get_setting, save_setting, delete_setting
from state_manager import broadcast_state

logger = logging.getLogger("app")

router = APIRouter(prefix="/api/settings", tags=["settings"])


# Pydantic models for request validation
class SettingIn(BaseModel):
    value: Any
    data_type: str = "string"
    description: Optional[str] = None


class SettingUpdate(BaseModel):
    settings: Dict[str, Any]


@router.get("")
async def get_all_settings_endpoint(db: Session = Depends(get_db)):
    """Get all settings"""
    return get_all_settings(db)


@router.get("/{key}")
async def get_setting_api(key: str, default: Optional[str] = None, db: Session = Depends(get_db)):
    """Get a specific setting by key"""
    value = get_setting(db, key, default)
    if value is None and default is None:
        raise HTTPException(status_code=404, detail=f"Setting {key} not found")
    return {"key": key, "value": value}


@router.post("/{key}")
async def set_setting(key: str, setting: SettingIn, db: Session = Depends(get_db)):
    """Set a specific setting"""
    success = save_setting(
        db,
        key=key,
        value=setting.value,
        data_type=setting.data_type,
        description=setting.description
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save setting")
    broadcast_state()
    return {"key": key, "value": setting.value, "status": "success"}


@router.post("")
async def update_multiple_settings(settings: SettingUpdate, db: Session = Depends(get_db)):
    """Update multiple settings at once"""
    results = {}
    gpio_enabled_changed = False
    gpio_enabled_new = None
    
    for key, value in settings.settings.items():
        if key == "gpio_enabled":
            gpio_enabled_changed = True
            gpio_enabled_new = value
            
        if isinstance(value, dict) and "value" in value:
            # Handle objects with value, data_type, description
            success = save_setting(
                db, 
                key, 
                value["value"], 
                value.get("data_type", "string"), 
                value.get("description", "")
            )
        else:
            # Handle simple key-value pairs
            success = save_setting(db, key, value)
            
        results[key] = "success" if success else "failed"
    
    broadcast_state()
    
    # Handle GPIO state changes
    if gpio_enabled_changed:
        if gpio_enabled_new in [True, "true", "True", 1, "1"]:
            try:
                from main import GPIO_AVAILABLE
                if GPIO_AVAILABLE:
                    from gpio_monitor import start_gpio_monitoring
                    start_gpio_monitoring()
                    logger.info("[settings] GPIO monitoring started")
                else:
                    from main import fallback_start_gpio_monitoring
                    fallback_start_gpio_monitoring()
            except Exception as e:
                logger.error(f"[settings] Failed to start GPIO monitoring: {e}")
        else:
            try:
                from main import GPIO_AVAILABLE
                if GPIO_AVAILABLE:
                    from gpio_monitor import set_alarm_states, stop_gpio_monitoring
                    set_alarm_states({"alarm1": False, "alarm2": False})
                    stop_gpio_monitoring()
                    logger.info("[settings] GPIO monitoring stopped")
                else:
                    from main import fallback_set_alarm_states, fallback_stop_gpio_monitoring
                    fallback_set_alarm_states({"alarm1": False, "alarm2": False})
                    fallback_stop_gpio_monitoring()
            except Exception as e:
                logger.error(f"[settings] Failed to stop GPIO monitoring: {e}")
    
    return results


@router.delete("/{key}")
async def delete_setting_endpoint(key: str, db: Session = Depends(get_db)):
    """Delete a setting"""
    success = delete_setting(db, key)
    if not success:
        raise HTTPException(status_code=404, detail=f"Setting {key} not found")
    broadcast_state()
    return {"status": "success", "message": f"Setting {key} deleted"}
