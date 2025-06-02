# services/robot_service.py
import threading
import time
import logging
from MecheyePackage.mecheye_trigger import robot
from MecheyePackage.ws_robot_state import ws_manager
from models.robot_state import state
from MecheyePackage.robot_control import send_command
from config import BASE_DIR
import os

logger = logging.getLogger(__name__)
robot_lock = threading.Lock()

ws_manager.connect()

# Global callback fonksiyonu için değişken
status_callback = None

send_command({"cmd":303,"data":{"mode":"1"}})

def set_status_callback(callback):
    """Robot status callback'ini ayarla"""
    global status_callback
    status_callback = callback

def get_robot_status(max_retries=10):
    retries = 0
    while retries < max_retries:
        try:
            # Yeni manager'dan veri al
            robot_state = ws_manager.get_robot_state()
            values = robot_state["di_values"]
            tcp = robot_state["tcp"]
            
            if values and tcp:
                tcp_tuple = tuple((0, [tcp["x"], tcp["y"], tcp["z"]]))
                return (
                    tuple([0, values["98"]]), 
                    tuple([0, values["99"]]), 
                    tuple([0, values["90"]]), 
                    tcp_tuple
                )
        except Exception as e:
            logger.error(f"get_robot_status error: {e}")
        
        retries += 1
        time.sleep(0.1)
    return -1

def robot_status_monitor():
    """Robot durumunu sürekli izleyen fonksiyon"""
    global di8, di9, di0, tcp
    logger.info("Robot status monitor started")
    
    while True:
        try:
            # Bağlantı kontrolü ekle
            if not ws_manager.is_connected():
                logger.warning("WebSocket bağlantısı yok, yeniden bağlanmaya çalışılıyor...")
                ws_manager.connect()
                time.sleep(1)
                continue
            
            # Robot verilerini al
            di8, di9, di0, tcp = get_robot_status()
            
            # Geri kalan kod aynı...
            state.update_di_values(di0=di0, di8=di8, di9=di9, tcp=tcp)
            status = state.get_status()
            
            if status_callback and status:
                status_callback('robot_status', status)
                
        except Exception as e:
            logger.error(f"Error in robot status monitor: {e}")
        
        time.sleep(0.1)

def safe_get_di(ch):
    if ch == 98:
        return di8
    elif ch == 99:
        return di9
    elif ch == 90:
        return di0
    else:
        logger.error(f"Invalid channel: {ch}")
        return -1

def read_current_point_index() -> int:
    file_path = str(BASE_DIR.parent / "backend" / "MecheyePackage" / "point_index.txt")
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            try:
                return int(file.read().strip())
            except ValueError as e:
                logger.error(f"Invalid value in point_index.txt: {e}")
                return 0
    return 0

def start_robot_service():
    """Robot servisini başlat (bağımsız thread)"""
    # Health check thread'i
    # health_thread = threading.Thread(target=health_check, daemon=True)
    # health_thread.start()
    
    # Robot status monitor thread'i
    status_thread = threading.Thread(target=robot_status_monitor, daemon=True)
    status_thread.start()
    
    logger.info("Robot service threads started")