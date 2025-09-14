# state_manager.py
"""
Legacy state manager - maintaining only essential functions for backward compatibility.
Most functionality has been moved to the event-driven architecture in modules/.
"""

import logging
from contextlib import contextmanager
from collections import deque
from typing import Optional

# Local imports
from db import get_db

logger = logging.getLogger("state_manager")

# Legacy serial log for routes that still need it
serial_log = deque(maxlen=30)
serial_active = False

# Database session wrapper for legacy compatibility
@contextmanager
def get_db_session():
    """Context manager for database sessions - legacy compatibility"""
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()


def get_current_patient_id() -> Optional[int]:
    """Get the current active patient ID for single-patient workflows"""
    try:
        with get_db_session() as db:
            from crud.patients import get_active_patient
            active_patient = get_active_patient(db)
            return active_patient.id if active_patient else None
    except Exception as e:
        logger.error(f"Error getting current patient ID: {e}")
        return None


def ensure_default_patient() -> Optional[int]:
    """Ensure a default patient exists and return its ID"""
    try:
        with get_db_session() as db:
            from crud.patients import get_or_create_default_patient
            patient = get_or_create_default_patient(db)
            return patient.id if patient else None
    except Exception as e:
        logger.error(f"Error ensuring default patient: {e}")
        return None


def get_serial_log():
    """Return the current serial log as a list - legacy compatibility"""
    logger.warning("Legacy get_serial_log() called - consider using event system")
    return list(serial_log)


def is_serial_mode() -> bool:
    """Return serial mode status - legacy compatibility"""
    logger.warning("Legacy is_serial_mode() called - consider using event system")
    return serial_active


def broadcast_state():
    """
    Legacy broadcast function - now handled by WebSocket module.
    Kept for backward compatibility.
    """
    logger.warning("Legacy broadcast_state() called - this should use the event system")
    # Event-driven system handles this now
    pass


def publish_specific_vital_to_mqtt(vital_type, vital_data):
    """
    Legacy MQTT publishing function - now handled by MQTT module.
    Kept for backward compatibility.
    """
    logger.warning(f"Legacy MQTT publish called for {vital_type} - this should use the event system")
    # Event-driven system handles this now
    pass


def update_sensor(*updates, from_mqtt=False):
    """
    Legacy sensor update function - now handled by event-driven modules.
    Kept for backward compatibility.
    """
    logger.warning("Legacy update_sensor() called - this should use the event system")
    # Event-driven system handles this now
    pass


def get_serial_log():
    """
    Legacy serial log function - should get from serial module.
    Returns empty list for backward compatibility.
    """
    logger.warning("Legacy get_serial_log() called - this should query the serial module")
    try:
        from main import get_modules
        modules = get_modules()
        serial_module = modules.get("serial")
        if serial_module and hasattr(serial_module, 'get_serial_log'):
            return serial_module.get_serial_log()
    except:
        pass
    return []


def is_serial_mode():
    """
    Legacy serial mode check - should get from serial module.
    Returns False for backward compatibility.
    """
    logger.warning("Legacy is_serial_mode() called - this should query the serial module")
    try:
        from main import get_modules
        modules = get_modules()
        serial_module = modules.get("serial")
        if serial_module and hasattr(serial_module, 'is_active'):
            return serial_module.is_active()
    except:
        pass
    return False


# Legacy WebSocket management (for routes that haven't been updated yet)
websocket_clients = set()

def register_websocket_client(ws):
    """Legacy WebSocket registration - use WebSocket module instead"""
    logger.warning("Legacy WebSocket registration - use WebSocket module instead")
    websocket_clients.add(ws)


def unregister_websocket_client(ws):
    """Legacy WebSocket unregistration - use WebSocket module instead"""
    logger.warning("Legacy WebSocket unregistration - use WebSocket module instead") 
    websocket_clients.discard(ws)
