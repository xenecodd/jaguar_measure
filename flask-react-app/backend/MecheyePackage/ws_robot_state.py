import json
import threading
import websocket
from MecheyePackage.robot_control import login, send_command
import time

import logging

logger = logging.getLogger(__name__)

counter = 0
start = time.time()

di_values = {
    "90": None,
    "98": None,
    "99": None
}

def most_common_value(lst):
    """Liste içindeki en sık tekrar eden değeri döndür."""
    if not lst:
        return None
    return max(set(lst), key=lst.count)

def on_message(_ws, message):
    global counter, start
    try:
        data = json.loads(message)
        counter += 1
        elapsed = time.time() - start  # Başlangıçtan geçen toplam süre

        # 10 saniyede bir toplam süreyi ve sayacı yazdır
        # if int(elapsed) % 10 == 0 and int(elapsed) != 0:
        #     print(f"{int(elapsed)} saniyede toplam {counter} mesaj")
        di_values["90"] = (data["value"]["90"][-1])
        di_values["98"] = (data["value"]["98"][-1])
        di_values["99"] = (data["value"]["99"][-1])
        # logger.error(f"di_values: {di_values}")
    except Exception as e:
        print("Mesaj parse hatası:", e)

def on_error(ws, error):
    print("Hata:", error)

def on_close(ws, close_status_code, close_msg):
    print("Bağlantı kapandı")

def on_open(ws):
    print("Bağlantı açıldı")
    # Komutları burada gönderebilirsin
    send_command({"cmd": 230, "data": {"type": 0, "id": ["90","98", "99"]}})
    send_command({"cmd": 231, "data": {"flag": "1"}})

def start_websocket(url):
    """WebSocket bağlantısını başlat."""
    cookies,header = login()  # Giriş yap ve cookie'leri al
    url =  "ws://192.168.58.2:9998/"   # WebSocket URL'sini buraya gir
    cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items())

    ws = websocket.WebSocketApp(
        url,
        header={"Cookie": cookie_header},
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
        on_open=on_open
    )

    thread = threading.Thread(target=ws.run_forever, kwargs={"ping_interval": 10000, "ping_timeout": 9000})
    thread.daemon = True
    thread.start()

    return ws