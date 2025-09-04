"""
Vitals and sensor data routes
"""
import logging
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from db import get_db
from crud.vitals import (get_vitals_by_type, get_distinct_vital_types, get_vitals_by_type_paginated, 
                  save_blood_pressure, save_temperature, save_vital)
from state_manager import broadcast_state, publish_specific_vital_to_mqtt

logger = logging.getLogger("app")

router = APIRouter(prefix="/api/vitals", tags=["vitals"])


@router.post("/manual")
async def add_manual_vitals(vital_data: dict, db: Session = Depends(get_db)):
    try:
        datetime_val = vital_data.get("datetime")
        notes = vital_data.get("notes")
        vitals_saved = []  # Track what vitals were actually saved
        
        # Handle blood pressure
        bp = vital_data.get("bp", {})
        if bp and (bp.get("systolic_bp") or bp.get("diastolic_bp")):
            systolic = bp.get("systolic_bp")
            diastolic = bp.get("diastolic_bp")
            map_bp = bp.get("map_bp")
            if systolic and diastolic:
                bp_id = save_blood_pressure(db, systolic, diastolic, map_bp, datetime_val, notes)
                if bp_id:
                    vitals_saved.append({
                        'type': 'blood_pressure',
                        'data': {'systolic': systolic, 'diastolic': diastolic, 'map': map_bp}
                    })
                
        # Handle temperature
        temp = vital_data.get("temp", {})
        if temp and temp.get("body_temp"):
            body_temp = temp.get("body_temp")
            temp_id = save_temperature(db, body_temp, datetime_val, notes)
            if temp_id:
                vitals_saved.append({
                    'type': 'temperature',
                    'data': {'temperature': body_temp}
                })
            
        # Handle bathroom
        bathroom_type = vital_data.get("bathroom_type")
        bathroom_size = vital_data.get("bathroom_size")
        bathroom_size_map = ["smear", "s", "m", "l", "xl"]
        if bathroom_type and bathroom_size:
            size_numeric = bathroom_size_map.index(bathroom_size) if bathroom_size in bathroom_size_map else 0
            vital_id = save_vital(db, "bathroom", size_numeric, datetime_val, notes, bathroom_type)
            if vital_id:
                vitals_saved.append({
                    'type': 'bathroom',
                    'data': {'type': bathroom_type, 'size': bathroom_size}
                })
        
        # Handle nutrition data (from frontend format)
        nutrition = vital_data.get("nutrition", {})
        if nutrition:
            calories = nutrition.get("calories")
            water = nutrition.get("water")
            if calories is not None and calories != "":
                cal_id = save_vital(db, "calories", calories, datetime_val, notes)
                if cal_id:
                    vitals_saved.append({
                        'type': 'calories', 
                        'data': {'calories': calories}
                    })
            if water is not None and water != "":
                water_id = save_vital(db, "water", water, datetime_val, notes)
                if water_id:
                    vitals_saved.append({
                        'type': 'water',
                        'data': {'water': water}
                    })
        
        # Handle weight
        weight = vital_data.get("weight")
        if weight is not None and weight != "":
            weight_id = save_vital(db, "weight", weight, datetime_val, notes)
            if weight_id:
                vitals_saved.append({
                    'type': 'weight',
                    'data': {'weight': weight}
                })
            
        # Dynamically handle any remaining vitals (excluding already processed ones)
        processed_keys = ["datetime", "bp", "temp", "nutrition", "weight", "notes", "bathroom_type", "bathroom_size"]
        for key, value in vital_data.items():
            if key not in processed_keys and value is not None and value != "":
                vital_id = save_vital(db, key, value, datetime_val, notes)
                if vital_id:
                    vitals_saved.append({
                        'type': key,
                        'data': {key: value}
                    })
            
        broadcast_state()
        
        # Publish each saved vital to MQTT if enabled
        print(f"[vitals] About to publish {len(vitals_saved)} vitals to MQTT: {[v['type'] for v in vitals_saved]}")
        for vital in vitals_saved:
            print(f"[vitals] Publishing {vital['type']} to MQTT")
            publish_specific_vital_to_mqtt(vital['type'], vital['data'])
            
        return {"status": "success", "message": "Vitals saved successfully"}
    except Exception as e:
        print(f"Error saving manual vitals: {str(e)}")
        return {"status": "error", "message": str(e)}


@router.get("/types")
def get_vital_types(db: Session = Depends(get_db)):
    """Get a distinct list of vital_type values from the vitals table"""
    return get_distinct_vital_types(db)


@router.get("/nutrition")
def get_nutrition_history(limit: int = 100, db: Session = Depends(get_db)):
    """Get combined nutrition history (calories and water)"""
    return {
        "calories": get_vitals_by_type(db, "calories", limit),
        "water": get_vitals_by_type(db, "water", limit)
    }


@router.get("/history")
def get_vital_history_paginated(vital_type: str, page: int = 1, page_size: int = 20, db: Session = Depends(get_db)):
    """Get paginated history for a specific vital type"""
    return get_vitals_by_type_paginated(db, vital_type, page, page_size)


@router.get("/{vital_type}")
def get_vital_history(vital_type: str, limit: int = 100, db: Session = Depends(get_db)):
    return get_vitals_by_type(db, vital_type, limit)
