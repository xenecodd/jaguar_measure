import threading
import time
import logging
import json

import websocket
from MecheyePackage.mecheye_trigger import TriggerWithExternalDeviceAndFixedRate
from MecheyePackage import ws_robot_state
import Robot

logger = logging.getLogger(__name__)
robot_lock = threading.Lock()

# Mekanik göz ve robot başlatma
mech_eye = TriggerWithExternalDeviceAndFixedRate()
robot = mech_eye.robot

cookies = ws_robot_state.load_cookies("services/cookie.json")  # Using relative path
ws_url = "ws://192.168.58.2:9998/"

ws = ws_robot_state.start_websocket(
    ws_url,
    cookies
)


def safe_get_di(channel, max_retries=10):
    retries = 0
    while retries < max_retries:
        try:
            raw_value = ws_robot_state.di_values.get(str(channel))
            if raw_value is not None:
                float_value = float(raw_value)  # önce string'ten float'a
                int_value = int(round(float_value))  # sonra tam sayıya
                return tuple([0,int_value])
        except Exception as e:
            logger.error(f"safe_get_di error: {e}")
        retries += 1
        time.sleep(0.1)
    return -1


def health_check():
    global robot
    time.sleep(5)
    while True:
        try:
            with robot_lock:
                robot.SetDO(6, 1)
                time.sleep(0.5)
                one = robot.GetDI(6, 0)
                time.sleep(0.5)
                robot.SetDO(6, 0)
                time.sleep(0.5)
                zero = robot.GetDI(6, 0)
                time.sleep(0.5)

            if one == (0, 1) and zero == (0, 0):
                logger.info("Robot is healthy")
            else:
                logger.warning("Robot is not healthy — reconnecting")
                with robot_lock:
                    robot.reconnect()
                time.sleep(1)
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            try:
                with robot_lock:
                    robot = Robot.RPC('192.168.58.2')
            except Exception as reconnect_error:
                logger.error(f"Failed to reconnect: {reconnect_error}")
            time.sleep(1)


def safe_get_tcp(max_retries=10):
    retries = 0
    while retries < max_retries:
        try:
            with robot_lock:
                result = robot.GetActualTCPPose()
                if isinstance(result, tuple) and result[1] == -1:
                    raise Exception("接收机器人状态字节 -1")
                return result
        except Exception as e:
            logger.error(f"safe_get_tcp error: {e}")
            retries += 1
            time.sleep(0.1)
    return (-1, -1, -1, -1, -1, -1)
