import time
from mecheye.shared import *
from mecheye.profiler import *
from mecheye.profiler_utils import *
import cv2
import numpy as np
from time import sleep
from multiprocessing import Lock
from .robot_control import send_command,login
import threading
import sys
sys.path.append('/home/eypan/Downloads/')
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

    def set_parameters(self):
        self.user_set = self.profiler.current_user_set()

        # Data Acquisition Trigger Source
        show_error(self.user_set.set_enum_value(
            DataAcquisitionTriggerSource.name, DataAcquisitionTriggerSource.Value_Software))

        # Line Scan Trigger Source
        show_error(self.user_set.set_enum_value(
            LineScanTriggerSource.name, LineScanTriggerSource.Value_FixedRate))

        # Software Trigger Rate
        show_error(self.user_set.set_float_value(
            SoftwareTriggerRate.name, 907.0))

        # Scan Line Count
        show_error(self.user_set.set_int_value(ScanLineCount.name, 3500))

        # Callback Retrieval Timeout
        show_error(self.user_set.set_int_value(CallbackRetrievalTimeout.name, 60000))

        # X-Axis Resolution
        show_error(self.user_set.set_float_value(
            XAxisResolution.name, 23.5))

        # Y-Axis Resolution
        self.user_set.set_float_value(
            YResolution.name, 154.0)

        # Laser Power
        show_error(self.user_set.set_int_value(LaserPower.name, 100))

        # Minimum Laser Line Width
        show_error(self.user_set.set_int_value(MinLaserLineWidth.name, 2))

        # Maximum Laser Line Width
        show_error(self.user_set.set_int_value(MaxLaserLineWidth.name, 30))

        # Analog Gain
        show_error(self.user_set.set_enum_value(
            AnalogGain.name, AnalogGain.Value_Gain_2))

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
            EnableBlindSpotFiltering.name, True))
            
        # Enable X-Axis Alignment58
        show_error(self.user_set.set_bool_value(
            EnableXAxisAlignment.name, True))

        # Exposure Mode
        show_error(self.user_set.set_enum_value(
            ExposureMode.name, ExposureMode.Value_Timed))

        # Exposure Time
        show_error(self.user_set.set_int_value(ExposureTime.name, 1000))

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

        # Set a large CallbackRetrievalTimeout
        show_error(self.user_set.set_int_value(CallbackRetrievalTimeout.name, 60000))

        self.callback = CustomAcquisitionCallback(self.data_width).__disown__()

        # Register the callback function
        status = self.profiler.register_acquisition_callback(self.callback)
        if not status.is_ok():
            show_error(status)
            return False

        # def start_scan_in_thread(cmd_data):
        #     def scan_task():
        #         send_command(cmd_data)

        #     # Thread oluştur ve başlat
        #     scan_thread = threading.Thread(target=scan_task)
        #     scan_thread.daemon = True  # Ana thread ile birlikte sonlanır
        #     scan_thread.start()
        #     scan_thread.join()  # Thread tamamlanmasını bekle

        # Komutları gönder
        send_command({"cmd": 105, "data": {"name": lua_name}})

        
        if lua_name == "small.lua":
            send_command({"cmd": 303, "data": {"mode": "1"}})

            send_command({"cmd": 1001, "data": {"pgline": "Lin(scrc2,100,-1,0,0)"}})

            status = self.profiler.start_acquisition()
            if not status.is_ok():
                show_error(status)
                return False

            if self.is_software_trigger:
                status = self.profiler.trigger_software()
                
            if not status.is_ok():
                show_error(status)
                return False
            # send_command({"cmd": 1001, "data": {"pgline": "Lin(V1,100,-1,0,0)"}})
            # Profil veri toplama işlemi
            while True:
                mutex.acquire()
                if self.callback.profile_batch.is_empty():
                    mutex.release()
                    sleep(0.5)
                else:
                    mutex.release()
                    break

            # point_H2 = [-585, 60, 445.005, -84.703, -89.947, 174.614]

            # robot.MoveCart(point_H2, 0, 0)

            status = self.profiler.stop_acquisition()
                
            h_2 = [-585.0269165039062, 80.00602722167967, 444.9610290527343, -90, -90, 180]
            ret = robot.MoveCart(h_2, 0, 0, vel=100)

            if not status.is_ok():
                show_error(status)
            self.profile_batch.append(self.callback.profile_batch)
             
        elif lua_name == "horizontal.lua":
            send_command({"cmd": 303, "data": {"mode": "1"}})
            send_command({"cmd": 1001, "data": {"pgline": "Lin(H1,100,-1,0,0)"}})

            status = self.profiler.start_acquisition()
            if not status.is_ok():
                show_error(status)
                return False

            if self.is_software_trigger:
                status = self.profiler.trigger_software()
                
            if not status.is_ok():
                show_error(status)
                return False

            # Profil veri toplama işlemi
            while True:
                mutex.acquire()
                if self.callback.profile_batch.is_empty():
                    mutex.release()
                    sleep(0.5)
                else:
                    mutex.release()
                    break
            status = self.profiler.stop_acquisition()

            h1_alt = [-534.997802734375, -100.006637573242, 515.0164184570312, -90, -90, 180]
            ret = robot.MoveCart(h1_alt, 0, 0, vel=100)
            if not status.is_ok():
                show_error(status)
            self.profile_batch.append(self.callback.profile_batch)    
                
        elif lua_name == "vertical.lua":
            send_command({"cmd": 303, "data": {"mode": "1"}})
                
            send_command({"cmd": 1001, "data": {"pgline": "Lin(90,100,-1,0,0)"}})
            # Tarama komutlarını sırasıyla gönder
            status = self.profiler.start_acquisition()
            if not status.is_ok():
                show_error(status)
                return False

            if self.is_software_trigger:
                status = self.profiler.trigger_software()
                
            if not status.is_ok():
                show_error(status)
                return False
            # send_command({"cmd": 1001, "data": {"pgline": "Lin(V1,100,-1,0,0)"}})
            # Profil veri toplama işlemi
            while True:
                mutex.acquire()
                if self.callback.profile_batch.is_empty():
                    mutex.release()
                    sleep(0.5)
                else:
                    mutex.release()
                    break

            status = self.profiler.stop_acquisition()

            # scrc = [-5.9326171875, -74.58998878403466, 91.40015857054455, -196.742946511448, 5.83406656095297, 89.98324856899752]
            # ret = robot.MoveJ(scrc, 0, 0, vel=100)
            
            if not status.is_ok():
                show_error(status)
            self.profile_batch.append(self.callback.profile_batch)  

        elif lua_name == "horizontal2.lua":
            send_command({"cmd": 303, "data": {"mode": "1"}})
            
            status = self.profiler.start_acquisition()
            if not status.is_ok():
                show_error(status)
                return False

            if self.is_software_trigger:
                status = self.profiler.trigger_software()
                
            if not status.is_ok():
                show_error(status)
                return False
            h2_alt = [-535.0000610351562, 79.98582458496092, 516.0106811523437, -90, -90, 180]
            robot.MoveL(h2_alt, 0, 0, vel=100)
            # Profil veri toplama işlemi
            while True:
                mutex.acquire()
                if self.callback.profile_batch.is_empty():
                    mutex.release()
                    sleep(0.5)
                else:
                    mutex.release()
                    break
            status = self.profiler.stop_acquisition()

            p_91 = [-424.9966430664062, 49.99317169189453, 573.0062866210938, -89.99864196777342, -0.00046733912313356996, 90.00043487548828]
            ret = robot.MoveCart(p_91, 0, 0, vel=100)
            if not status.is_ok():
                show_error(status)
            self.profile_batch.append(self.callback.profile_batch)    
        return True



    def save_depth_and_intensity(self, depth_file_name, intensity_file_name):
        cv2.imwrite(depth_file_name,
                    self.profile_batch.get_depth_map().data())
        cv2.imwrite(intensity_file_name,
                    self.profile_batch.get_intensity_image().data())

    def main(self, lua_name):
        start_time = time.time()
        if not find_and_connect(self.profiler):
            return -1
        self.set_parameters()

        self.profile_batch = ProfileBatch(self.data_width)

        if not self.acquire_profile_data_using_callback(lua_name):
            return -1

        if self.profile_batch.check_flag(ProfileBatch.BatchFlag_Incomplete):
            print("Part of the batch's data is lost, the number of valid profiles is:",
                self.profile_batch.valid_height())

        points = save_point_cloud(profile_batch=self.profile_batch, user_set=self.user_set, save_csv=False, save_ply=False, save_np=True)

        self.profiler.disconnect()

        end_time = time.time()
        return points


if __name__ == '__main__':
    a = TriggerWithExternalDeviceAndFixedRate()
    a.main()