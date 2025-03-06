import time
from mecheye.shared import *
from mecheye.profiler import *
from mecheye.profiler_utils import *
import cv2
import numpy as np
from time import sleep
from multiprocessing import Lock
from robot_control import send_command, login
import threading
import sys
sys.path.append('/home/eypan/Downloads/fair_api_old/')
import Robot # type: ignore

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
    def __init__(self):
        self.profiler = Profiler()

    def set_timed_exposure(self, exposure_time: int):
        # Set the exposure mode to timed
        show_error(self.user_set.set_enum_value(
            ExposureMode.name, ExposureMode.Value_Timed))

        # Set the exposure time to {exposure_time} μs
        show_error(self.user_set.set_int_value(
            ExposureTime.name, exposure_time))

    def set_hdr_exposure(self, exposure_time: int, proportion1: float, proportion2: float, first_threshold: float, second_threshold: float):
        # Set the "Exposure Mode" parameter to "HDR"
        show_error(self.user_set.set_enum_value(
            ExposureMode.name, ExposureMode.Value_HDR))

        # Set the total exposure time to {exposure_time} μs
        show_error(self.user_set.set_int_value(
            ExposureTime.name, exposure_time))

        # Set the proportion of the first exposure phase to {proportion1}%
        show_error(self.user_set.set_float_value(
            HdrExposureTimeProportion1.name, proportion1))

        # Set the proportion of the first + second exposure phases to {proportion2}% (that is, the
        # second exposure phase occupies {proportion2 - proportion1}%, and the third exposure phase
        # occupies {100 - proportion2}% of the total exposure time)
        show_error(self.user_set.set_float_value(
            HdrExposureTimeProportion2.name, proportion2))

        # Set the first threshold to {first_threshold}. This limits the maximum grayscale value to
        # {first_threshold} after the first exposure phase is completed.
        show_error(self.user_set.set_float_value(
            HdrFirstThreshold.name, first_threshold))

        # Set the second threshold to {second_threshold}. This limits the maximum grayscale value to
        # {second_threshold} after the second exposure phase is completed.
        show_error(self.user_set.set_float_value(
            HdrSecondThreshold.name, second_threshold))

    def set_parameters(self,scan_line_count):
        self.user_set = self.profiler.current_user_set()

        # Data Acquisition Trigger Source
        show_error(self.user_set.set_enum_value(
            DataAcquisitionTriggerSource.name, DataAcquisitionTriggerSource.Value_Software))

        # Line Scan Trigger Source
        show_error(self.user_set.set_enum_value(
            LineScanTriggerSource.name, LineScanTriggerSource.Value_FixedRate))

        # Software Trigger Rate
        show_error(self.user_set.set_float_value(
            SoftwareTriggerRate.name, 2665.0))

        # Scan Line Count
        show_error(self.user_set.set_int_value(ScanLineCount.name, scan_line_count))

        # Callback Retrieval Timeout
        show_error(self.user_set.set_int_value(CallbackRetrievalTimeout.name, 60000))

        # # X-Axis Resolution
        # show_error(self.user_set.set_float_value(
        #     XAxisResolution.name, 23.5))
        # print("X-Axis Resolution", XAxisResolution.unit, XAxisResolution.description, XAxisResolution.type)
        # # Y-Axis Resolution
        # self.user_set.set_float_value(
        #     YResolution.name, 50)

        # Laser Power
        show_error(self.user_set.set_int_value(LaserPower.name, 100))

        # Minimum Laser Line Width
        show_error(self.user_set.set_int_value(MinLaserLineWidth.name, 2))

        # Maximum Laser Line Width
        show_error(self.user_set.set_int_value(MaxLaserLineWidth.name, 30))

        # Analog Gain
        show_error(self.user_set.set_enum_value(
            AnalogGain.name, AnalogGain.Value_Gain_5))

        # Digital Gain
        show_error(self.user_set.set_int_value(DigitalGain.name, 0))

        # Minimum Grayscale Value
        show_error(self.user_set.set_int_value(MinGrayscaleValue.name, 50))

        # Spot Selection
        show_error(self.user_set.set_enum_value(
            SpotSelection.name, SpotSelection.Value_Strongest))

        # Minimum Laser Spot Intensity
        show_error(self.user_set.set_int_value(MinSpotIntensity.name, 51))

        # Maximum Laser Spot Intensity
        show_error(self.user_set.set_int_value(MaxSpotIntensity.name, 205))

        # Gap Filling5000
        show_error(self.user_set.set_enum_value(
            Filter.name, Filter.Value_Mean))

        # Mean Filter Window Size
        show_error(self.user_set.set_enum_value(
            MeanFilterWindowSize.name, MeanFilterWindowSize.Value_WindowSize_2))

        # Enable Blind Spot Filtering
        show_error(self.user_set.set_bool_value(
            EnableBlindSpotFiltering.name, False))
            
        # Enable X-Axis Alignment58
        show_error(self.user_set.set_bool_value(
            EnableXAxisAlignment.name, False))

        # Exposure Mode
        show_error(self.user_set.set_enum_value(
            ExposureMode.name, ExposureMode.Value_Timed))

        # Exposure Time
        show_error(self.user_set.set_int_value(ExposureTime.name, 220))

        # Retrieve current values for validation or debugging
        error, self.data_width = self.user_set.get_int_value(DataPointsPerProfile.name)
        show_error(error)

        error, self.capture_line_count = self.user_set.get_int_value(ScanLineCount.name)
        show_error(error)

        # Check if the "Data Acquisition Trigger Source" is set to Software
        error, data_acquisition_trigger_source = self.user_set.get_enum_value(DataAcquisitionTriggerSource.name)
        show_error(error)
        self.is_software_trigger = data_acquisition_trigger_source == DataAcquisitionTriggerSource.Value_Software


    def acquire_profile_data(self) -> bool:
        """
        Call start_acquisition() to enter the laser profiler into the acquisition ready status, and
        then call trigger_software() to start the data acquisition (triggered by software).
        """
        print("Start data acquisition.")
        status = self.profiler.start_acquisition()
        if not status.is_ok():
            show_error(status)
            return False

        if self.is_software_trigger:
            status = self.profiler.trigger_software()
            if (not status.is_ok()):
                show_error(status)
                return False

        self.profile_batch.clear()
        self.profile_batch.reserve(self.capture_line_count)

        while self.profile_batch.height() < self.capture_line_count:
            # Retrieve the profile data
            batch = ProfileBatch(self.data_width)
            status = self.profiler.retrieve_batch_data(batch)
            if status.is_ok():
                self.profile_batch.append(batch)
                sleep(0.2)
            else:
                show_error(status)
                return False

        status = self.profiler.stop_acquisition()
        if not status.is_ok():
            show_error(status)
        return status.is_ok()

    def acquire_profile_data_using_callback(self, lua_name) -> bool:
        self.profile_batch.clear()

        show_error(self.user_set.set_int_value(CallbackRetrievalTimeout.name, 60000))
        self.callback = CustomAcquisitionCallback(self.data_width).__disown__()

        status = self.profiler.register_acquisition_callback(self.callback)
        if not status.is_ok():
            show_error(status)
            return False

        send_command({"cmd": 105, "data": {"name": lua_name}})

        extra_commands = [{"cmd": 303, "data": {"mode": "1"}}]
        pre_move = None
        post_move = None
        pre_post_move = None
        
        scrc2 = [-450, 130, 470, 82.80, 89.93, -7.30]
        p90    = [-335, -350, 450, -90, 0, 90]
        p91    = [-335, 200, 450, -90, 0, 90]
        h1     = [-375, -120, 580, -90, -90, 180]
        h2     = [-367, 200, 580, -90, -90, 180]
        h1_alt = [-425, -120, 510, -90, -90, 180]
        h2_alt = [-418, 200, 510, -90, -90, 180]

        if lua_name == "small.lua":
            pre_move = ("MoveL", scrc2)
            # pre_post_move = ("MoveL", [-500.0104370117187, 100, 450, 82.15313720703125, 89.94375610351562, -7.949760913848877])
            post_move = ("MoveCart", h2)
        elif lua_name == "horizontal.lua":
            pre_move = ("MoveL", h1)
            post_move = ("MoveCart", h1_alt)
        elif lua_name == "horizontal2.lua":
            pre_move = ("MoveL", h2_alt)
            # pre_post_move = ("MoveL", [-535.0000610351562, 79.98582458496092, 416, -90, -90, 180])
            post_move = ("MoveCart", p91)
        elif lua_name == "vertical.lua":
            pre_move = ("MoveL", p90)


        
        for cmd in extra_commands:
            send_command(cmd)

        if pre_move:
            threading.Thread(target=self._move_robot, args=pre_move).start() #self._move_robot(*pre_move)
        
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

        # if pre_post_move:
        #     self._move_robot(*pre_post_move,vel_cart=100,vel_l=100)
        #     pre_post_move=None

        if post_move:
            self._move_robot(*post_move)

        self.profile_batch.append(self.callback.profile_batch)
        return True



    def _move_robot(self, move_type: str, coordinates: list,vel_cart=54,vel_l = 54):
        if move_type == "MoveCart":
            robot.MoveCart(coordinates, 0, 0, vel = vel_cart)
        elif move_type == "MoveL":
            robot.MoveL(coordinates, 0, 0, vel= vel_l)
        elif move_type == "MoveJ":
            robot.MoveJ(coordinates, 0, 0, vel=100)
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
        cv2.imwrite(depth_file_name,
                    self.profile_batch.get_depth_map().data())
        cv2.imwrite(intensity_file_name,
                    self.profile_batch.get_intensity_image().data())

    def main(self, lua_name, scan_line_count=4000):
        start_time = time.time()
        if not find_and_connect(self.profiler):
            return -1
        end_time = time.time()-start_time
        print(f"Connection Time: {end_time}")
        self.set_parameters(scan_line_count)

        self.profile_batch = ProfileBatch(self.data_width)

        if not self.acquire_profile_data_using_callback(lua_name):
            return -1

        if self.profile_batch.check_flag(ProfileBatch.BatchFlag_Incomplete):
            print("Part of the batch's data is lost, the number of valid profiles is:",
                self.profile_batch.valid_height())

        points = save_point_cloud(profile_batch=self.profile_batch, user_set=self.user_set, save_csv=False, save_ply=False, save_np=True)

        start_time = time.time()
        self.profiler.disconnect()

        end_time = time.time()-start_time
        print(f"Disconnection Time: {end_time}")

        return points


if __name__ == '__main__':
    a = TriggerWithExternalDeviceAndFixedRate()
    a.main()