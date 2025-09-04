# state_manager.py
"""
Legacy state manager - maintaining only essential functions for backward compatibility.
Most functionality has been moved to the event-driven architecture in modules/.
"""

import logging
from contextlib import contextmanager

# Local imports
from db import get_db

logger = logging.getLogger("state_manager")

# Database session wrapper for legacy compatibility
@contextmanager
def get_db_session():
    """Context manager for database sessions - legacy compatibility"""
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()


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
