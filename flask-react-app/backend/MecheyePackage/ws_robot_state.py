import json
import threading
import websocket
import time
from MecheyePackage.robot_control import login
import logging

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self, url="ws://192.168.58.2:9999/"):
        self.connection_status = 0  # 0: kapalı, 1: açık
        self.socket_error = False
        self.logout_flag = False

        self.ws_instance = None
        self.url = url
        self.cookies = None

        self.reconnect_timer = None
        self.reconnect_interval = None
        self.retry_count = 0
        self.max_retries = 5
        self.base_retry_delay = 0.5

        self.lock = threading.Lock()

        self.di_values = [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,]  # DI0-DI15
        self.tcp = [3, 3, 3, 3, 3, 3] # x,y,z,rx,ry,rz

        self.mode = 1

    def clear_timers(self):
        if self.reconnect_timer:
            self.reconnect_timer.cancel()
            self.reconnect_timer = None
        if self.reconnect_interval:
            self.reconnect_interval.cancel()
            self.reconnect_interval = None

    def on_message(self, ws, message):
        try:
            data = json.loads(message)

            if message == 'websocket close':
                logger.warning("Sunucu logout mesajı gönderdi")
                self.logout_flag = True
                self.connection_status = 0
                return

            if not isinstance(data, dict):
                logger.warning("Geçersiz mesaj formatı, logout yapılıyor")
                self.logout_flag = True
                self.connection_status = 0
                return

            with self.lock:
                if "cl_di" in data:
                    self.di_values[0] = data["cl_di"][0]
                    self.di_values[1] = data["cl_di"][1]
                    self.di_values[2] = data["cl_di"][2]
                    self.di_values[3] = data["cl_di"][3]
                    self.di_values[4] = data["cl_di"][4]
                    self.di_values[5] = data["cl_di"][5]
                    self.di_values[6] = data["cl_di"][6]
                    self.di_values[7] = data["cl_di"][7]
                    self.di_values[8] = data["cl_di"][8]
                    self.di_values[9] = data["cl_di"][9]
                    self.di_values[10] = data["cl_di"][10]
                    self.di_values[11] = data["cl_di"][11]
                    self.di_values[12] = data["cl_di"][12]
                    self.di_values[13] = data["cl_di"][13]
                    self.di_values[14] = data["cl_di"][14]
                    self.di_values[15] = data["cl_di"][15]

                if "tcp" in data:
                    self.tcp = data["tcp"]

                if "mode" in data:
                    self.mode = data["mode"]
                    
                self.connection_status = 1
                self.logout_flag = False
                self.retry_count = 0

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse hatası: {e}")
        except Exception as e:
            logger.error(f"Mesaj işleme hatası: {e}")

    def on_error(self, ws, error):
        
        with self.lock:
            self.socket_error = True
            self.connection_status = 0
        logger.error(f"WebSocket hatası: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        
        with self.lock:
            self.connection_status = 0
        logger.warning(f"Bağlantı kapandı - Status: {close_status_code}, Mesaj: {close_msg}")
        self.clear_timers()
        if not self.logout_flag:
            self._schedule_reconnect()

    def on_open(self, ws):
        with self.lock:
            self.socket_error = False
            self.connection_status = 1
            self.retry_count = 0
        logger.info("WebSocket bağlantısı açıldı")
        self.clear_timers()

    def _schedule_reconnect(self):
        if self.retry_count >= self.max_retries:
            logger.error(f"Maksimum deneme sayısına ulaşıldı ({self.max_retries})")
            return

        delay = self.base_retry_delay * (2 ** self.retry_count)
        delay = min(delay, 30)
        logger.info(f"Yeniden bağlanma {delay} saniye sonra denenecek (deneme: {self.retry_count + 1})")

        self.reconnect_timer = threading.Timer(delay, self._attempt_reconnect)
        self.reconnect_timer.start()

    def _attempt_reconnect(self):
        
        if self.logout_flag:
            logger.info("Manuel kapanma, yeniden bağlanma iptal edildi")
            return

        with self.lock:
            self.retry_count += 1

        logger.info(f"Yeniden bağlanma denemesi: {self.retry_count}")

        try:
            self._close_connection()
            time.sleep(0.1)

            logger.info("Yeni login yapılıyor...")
            self.cookies, _ = login()
            self._create_connection()

        except Exception as e:
            logger.error(f"Yeniden bağlanma hatası: {e}")
            if not self.logout_flag:
                self._schedule_reconnect()

    def _close_connection(self):
        if self.ws_instance:
            try:
                self.ws_instance.close()
                logger.info("Önceki WebSocket bağlantısı kapatıldı")
            except Exception as e:
                logger.warning(f"Bağlantı kapatılırken hata: {e}")
            finally:
                self.ws_instance = None

    def _create_connection(self):
        if not self.cookies:
            raise Exception("Cookie alınamadı")

        cookie_header = "; ".join(f"{k}={v}" for k, v in self.cookies.items())

        self.ws_instance = websocket.WebSocketApp(
            self.url,
            header={"Cookie": cookie_header},
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open
        )

        thread = threading.Thread(
            target=self.ws_instance.run_forever,
            kwargs={"ping_interval": None, "ping_timeout": None}
        )
        thread.daemon = True
        thread.start()

    def connect(self):
        
        with self.lock:
            if self.connection_status == 1:
                logger.info("Zaten bağlı durumda")
                return True

            self.logout_flag = False
            self.socket_error = False
            self.retry_count = 0

        try:
            logger.info("Login yapılıyor...")
            self.cookies, _ = login()
            self._create_connection()
            return True

        except Exception as e:
            logger.error(f"Bağlantı hatası ws_robot_state: {e}")
            return False

    def disconnect(self):
        with self.lock:
            self.logout_flag = True
            self.connection_status = 0

        self.clear_timers()
        self._close_connection()
        logger.info("WebSocket bağlantısı manuel olarak kesildi")

    def is_connected(self):
        with self.lock:
            return self.connection_status == 1

    def get_robot_state(self):
        with self.lock:
            return {
                "di_values": self.di_values,
                "tcp": self.tcp,
                "mode": self.mode,
                "connection_status": self.connection_status,
                "socket_error": self.socket_error
            }

# Global instance
ws_manager = WebSocketManager()

# Backward compatibility fonksiyonları
def initialize_websocket():
    return ws_manager.connect()

def start_websocket():
    return ws_manager.connect()

def get_di_values():
    return ws_manager.di_values

def get_tcp():
    return ws_manager.tcp

def get_mode():
    return ws_manager.mode