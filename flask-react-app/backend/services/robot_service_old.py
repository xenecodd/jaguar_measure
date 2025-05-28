import threading
import time
import logging
from concurrent.futures import ThreadPoolExecutor
from MecheyePackage.mecheye_trigger import robot
import sys
from pathlib import Path
from fair_api import Robot

logger = logging.getLogger(__name__)

robot_lock = threading.Lock()

# Thread havuzu oluştur
executor = ThreadPoolExecutor(max_workers=5)  # Maksimum 5 thread

def safe_get_di(channel, index=0, max_retries=10):
    retries = 0
    if channel == 98:
        channel = 8
    elif channel == 99:
        channel = 9
    elif channel == 90:
        channel = 0
    
    while retries < max_retries:
        try:
            def _get_di():
                with robot_lock:
                    result = robot.GetDI(channel, index)
                    # logger.error(f"GetDI result: {result}")
                if isinstance(result, tuple) and result[1] == -1:
                    raise Exception("接收机器人状态字节 -1")
                return result

            # Thread havuzunda çalıştır
            future = executor.submit(_get_di)
            result = future.result(timeout=2.0)  # 2 saniye içinde sonuç bekleniyor
            # logger.error(f"GetDI result: {result])}")
            return result
        except Exception as e:
            retries += 1
            if "接收机器人状态字节 -1" in str(e) and retries < max_retries:
                try:
                    with robot_lock:
                        Robot.RPC.reconnect()
                except:
                    time.sleep(1)
                time.sleep(0.5)
            else:
                if retries >= max_retries:
                    return (-8, -7)
                raise e
    return (-4, -6)


def safe_get_tcp(max_retries=10):
    retries = 0
    while retries < max_retries:
        try:
            result_container = []

            def _get_tcp():
                try:
                    with robot_lock:
                        result = robot.GetActualTCPPose()
                    if isinstance(result, tuple) and result[1] == -1:
                        raise Exception("接收机器人状态字节 -1")
                    result_container.append(result)
                except Exception as e:
                    result_container.append(e)

            t = threading.Thread(target=_get_tcp)
            t.daemon = True
            t.start()
            t.join(2.0)

            if not result_container:
                retries += 1
                continue
            if isinstance(result_container[0], Exception):
                raise result_container[0]
            return result_container[0]
        except Exception as e:
            retries += 1
            if "接收机器人状态字节 -1" in str(e) and retries < max_retries:
                try:
                    with robot_lock:
                        Robot.RPC.reconnect()
                except:
                    time.sleep(1)
                time.sleep(0.5)
            else:
                if retries >= max_retries:
                    return (-1, -1, -1, -1, -1, -1)
                raise e
    return (-1, -1, -1, -1, -1, -1)