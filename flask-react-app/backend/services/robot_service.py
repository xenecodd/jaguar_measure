# services/robot_service.py
import threading
import time
import logging
from MecheyePackage.ws_robot_state import ws_manager
from models.robot_state import state
from config import BASE_DIR
import os

logger = logging.getLogger(__name__)
robot_lock = threading.Lock()

ws_manager.connect()

# Global callback fonksiyonu için değişken
status_callback = None

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
            di_values = robot_state["di_values"]
            tcp = robot_state["tcp"]
            mode = robot_state["mode"]
            
            if di_values and tcp:
                return (
                    di_values,  # Tüm DI değerleri (DI0-DI15)
                    tcp,        # TCP değerleri
                    mode        # Mode değeri
                )
        except Exception as e:
            logger.error(f"get_robot_status error: {e}")
        
        retries += 1
        time.sleep(0.1)
    return -1

def robot_status_monitor():
    """Robot durumunu sürekli izleyen fonksiyon"""
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
            result = get_robot_status()
            if result != -1:
                di_values, tcp, mode = result
                
                # State'i güncelle
                state.update_di_values(di_values=di_values, tcp=tcp, mode=mode)
                status = state.get_status()
                
                if status_callback and status:
                    status_callback('robot_status', status)
                
        except Exception as e:
            logger.error(f"Error in robot status monitor: {e}")
        
        time.sleep(0.1)

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

def write_current_point_index(index: int):
    file_path = str(BASE_DIR.parent / "backend" / "MecheyePackage" / "point_index.txt")
    with open(file_path, 'w') as file:
        file.write(str(index))

def start_robot_service():
    """Robot servisini başlat (bağımsız thread)"""
    
    # Robot status monitor thread'i
    status_thread = threading.Thread(target=robot_status_monitor, daemon=True)
    status_thread.start()
    
    logger.info("Robot service threads started")