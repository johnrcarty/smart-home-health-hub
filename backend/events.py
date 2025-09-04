# events.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

@dataclass(frozen=True)
class SensorUpdate:
    """Generic sensor key/value update (matches your current update_sensor input)."""
    ts: datetime
    values: Dict[str, Any]           # e.g. {"spo2": 97, "bpm": 88}
    raw: Optional[str] = None
    source: str = "serial"           # "serial" | "mqtt" | "gpio" | etc.

@dataclass(frozen=True)
class AlarmPanelState:
    ts: datetime
    alarm1: bool
    alarm2: bool
