# backend/sockets/robot_status_socket.py

import time
import logging
import threading

from models.robot_state import state
from services.robot_service import safe_get_di  

logger = logging.getLogger(__name__)

def register_socket_events(socketio):
    def update_robot_status():
        while True:
            try:
                di8 = safe_get_di(8, 0)
                di9 = safe_get_di(9, 0)
                di0 = safe_get_di(0, 0)
                # state güncellemesi:
                state.update_di_values(di0=di0, di8=di8, di9=di9, tcp=[0, 0, 0, 0, 0, 0])
                status = state.get_status()
                if status:
                    socketio.emit('robot_status', status)
            except Exception as e:
                logger.error(f"Error updating robot status: {e}")
            time.sleep(0.2)

    # Bu thread, her zaman arka planda robot durumunu güncelleyecek:
    status_thread = threading.Thread(target=update_robot_status, daemon=True)
    status_thread.start()
