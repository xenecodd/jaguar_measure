import time
from mecheye.shared import *
from mecheye.profiler import *
from mecheye.profiler_utils import *
import cv2
import numpy as np
from time import sleep
from multiprocessing import Lock
import threading
import sys
from pathlib import Path
from fair_api import Robot
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
if not logger.handlers:
    logger.addHandler(handler)

profiler = Profiler()
if not find_and_connect(profiler):
    logger.error("Could not connect to the profiler. Please check the connection and try again.")
robot = Robot.RPC('192.168.58.2')
mutex = Lock()

class CustomAcquisitionCallback(AcquisitionCallbackBase):
    def __init__(self, width):
        AcquisitionCallbackBase.__init__(self)
        self.profile_batch = ProfileBatch(width)

    def run(self, batch):
        mutex.acquire()
        self.profile_batch.append(batch)
        mutex.release()


class TriggerWithExternalDeviceAndFixedRate(object):
    def __init__(self, vel_mul=1):
        self.profiler = profiler
        self.vel_mul = vel_mul
        self.robot = robot
        self.current_di0_value = (0, 0)

    def set_timed_exposure(self, exposure_time: int):
        show_error(self.user_set.set_enum_value(ExposureMode.name, ExposureMode.Value_Timed))
        show_error(self.user_set.set_int_value(ExposureTime.name, exposure_time))

    def set_hdr_exposure(self, exposure_time: int, proportion1: float, proportion2: float, first_threshold: float, second_threshold: float):
        show_error(self.user_set.set_enum_value(ExposureMode.name, ExposureMode.Value_HDR))
        show_error(self.user_set.set_int_value(ExposureTime.name, exposure_time))
        show_error(self.user_set.set_float_value(HdrExposureTimeProportion1.name, proportion1))
        show_error(self.user_set.set_float_value(HdrExposureTimeProportion2.name, proportion2))
        show_error(self.user_set.set_float_value(HdrFirstThreshold.name, first_threshold))
        show_error(self.user_set.set_float_value(HdrSecondThreshold.name, second_threshold))

    def set_parameters(self, scan_line_count):
        self.user_set = self.profiler.current_user_set()

        show_error(self.user_set.set_enum_value(DataAcquisitionTriggerSource.name, DataAcquisitionTriggerSource.Value_Software))
        show_error(self.user_set.set_enum_value(LineScanTriggerSource.name, LineScanTriggerSource.Value_FixedRate))
        show_error(self.user_set.set_float_value(SoftwareTriggerRate.name, 2665.0))
        show_error(self.user_set.set_int_value(ScanLineCount.name, scan_line_count))
        show_error(self.user_set.set_int_value(CallbackRetrievalTimeout.name, 60000))

        show_error(self.user_set.set_int_value(LaserPower.name, 100))
        show_error(self.user_set.set_int_value(MinLaserLineWidth.name, 2))
        show_error(self.user_set.set_int_value(MaxLaserLineWidth.name, 30))
        show_error(self.user_set.set_enum_value(AnalogGain.name, AnalogGain.Value_Gain_5))
        show_error(self.user_set.set_int_value(DigitalGain.name, 0))
        show_error(self.user_set.set_int_value(MinGrayscaleValue.name, 50))
        show_error(self.user_set.set_enum_value(SpotSelection.name, SpotSelection.Value_Strongest))
        show_error(self.user_set.set_int_value(MinSpotIntensity.name, 51))
        show_error(self.user_set.set_int_value(MaxSpotIntensity.name, 205))
        show_error(self.user_set.set_enum_value(Filter.name, Filter.Value_Mean))
        show_error(self.user_set.set_enum_value(MeanFilterWindowSize.name, MeanFilterWindowSize.Value_WindowSize_2))
        show_error(self.user_set.set_bool_value(EnableBlindSpotFiltering.name, False))
        show_error(self.user_set.set_bool_value(EnableXAxisAlignment.name, False))
        show_error(self.user_set.set_enum_value(ExposureMode.name, ExposureMode.Value_Timed))
        show_error(self.user_set.set_int_value(ExposureTime.name, 220))

        error, self.data_width = self.user_set.get_int_value(DataPointsPerProfile.name)
        show_error(error)
        error, self.capture_line_count = self.user_set.get_int_value(ScanLineCount.name)
        show_error(error)
        error, data_acquisition_trigger_source = self.user_set.get_enum_value(DataAcquisitionTriggerSource.name)
        show_error(error)
        self.is_software_trigger = data_acquisition_trigger_source == DataAcquisitionTriggerSource.Value_Software

    def acquire_profile_data_using_callback(self, lua_name) -> bool:
        self.profile_batch.clear()
        show_error(self.user_set.set_int_value(CallbackRetrievalTimeout.name, 60000))
        self.callback = CustomAcquisitionCallback(self.data_width).__disown__()

        status = self.profiler.register_acquisition_callback(self.callback)
        if not status.is_ok():
            show_error(status)
            return False

        extra_commands = [{"cmd": 303, "data": {"mode": "1"}}]
        pre_move = None
        post_move = None

        scrc2 = [-450, 130, 470, 82.80, 89.93, -7.30]
        p90 = [-335, -400, 450, -90, 0, 90]
        p91 = [-335, 250, 450, -90, 0, 90]
        h1 = [-375, -120, 580, -90, -90, 180]
        h2 = [-375, 200, 580, -90, -90, 180]
        h1_alt = [-425, -120, 510, -90, -90, 180]
        h2_alt = [-425, 200, 510, -90, -90, 180]

        if lua_name == "small.lua":
            pre_move = ("MoveL", scrc2)
            post_move = ("MoveCart", h2)
        elif lua_name == "horizontal.lua":
            pre_move = ("MoveL", h1)
            post_move = ("MoveCart", h1_alt)
        elif lua_name == "horizontal2.lua":
            pre_move = ("MoveL", h2_alt)
            post_move = ("MoveCart", p91)
        elif lua_name == "vertical.lua":
            pre_move = ("MoveL", p90)

        if pre_move:
            print(f"Before pre move {lua_name}:", self.robot.GetActualTCPPose()[1])
            threading.Thread(target=self._move_robot, args=pre_move).start()

        status = self.profiler.start_acquisition()
        if not status.is_ok():
            show_error(status)
            return False

        if self.is_software_trigger:
            status = self.profiler.trigger_software()
            if not status.is_ok():
                show_error(status)
                return False

        self._wait_for_profile_data()

        status = self.profiler.stop_acquisition()
        if not status.is_ok():
            show_error(status)

        if post_move:
            print(f"Before post move: {lua_name}", self.robot.GetActualTCPPose()[1])
            self._move_robot(*post_move)

        self.profile_batch.append(self.callback.profile_batch)
        return True

    def _move_robot(self, move_type: str, coordinates: list, vel_cart=54, vel_l=54):
        if move_type == "MoveCart":
            self.robot.MoveCart(coordinates, 0, 0, vel=self.vel_mul * vel_cart)
        elif move_type == "MoveL":
            self.robot.MoveL(coordinates, 0, 0, vel=self.vel_mul * vel_l)
        elif move_type == "MoveJ":
            self.robot.MoveJ(coordinates, 0, 0, vel=self.vel_mul * 100)
        else:
            raise ValueError(f"Unsupported move type: {move_type}")

    def _wait_for_profile_data(self):
        while True:
            with mutex:
                empty = self.callback.profile_batch.is_empty()
            if empty:
                sleep(0.5)
            else:
                break

    def save_depth_and_intensity(self, depth_file_name, intensity_file_name):
        cv2.imwrite(depth_file_name, self.profile_batch.get_depth_map().data())
        cv2.imwrite(intensity_file_name, self.profile_batch.get_intensity_image().data())

    def main(self, lua_name, scan_line_count=4000):
        self.set_parameters(scan_line_count)

        self.profile_batch = ProfileBatch(self.data_width)

        if not self.acquire_profile_data_using_callback(lua_name):
            return -1

        if self.profile_batch.check_flag(ProfileBatch.BatchFlag_Incomplete):
            print("Part of the batch's data is lost, the number of valid profiles is:",
                  self.profile_batch.valid_height())

        points = save_point_cloud(profile_batch=self.profile_batch, user_set=self.user_set, save_csv=False, save_ply=False, save_np=True)
        
        return points
