import os
import sqlite3
import threading
import time
import numpy as np
import requests
import open3d as o3d
import matplotlib
from Scripts import *
from mecheye_trigger import TriggerWithExternalDeviceAndFixedRate
from points import *
import sys
import json
import mysql.connector
import logging
from typing import Dict
import socketio
from ResultWriter import AppwriteDataWriter

DEVICE_IP = os.environ.get('IP_ADDRESS')
PORT = os.environ.get('PORT')
if not DEVICE_IP or not PORT:
    raise EnvironmentError('Environment variables REACT_APP_DEVICE_IP and REACT_APP_PORT must be set')

API_BASE_URL = f"http://{DEVICE_IP}:{PORT}"

logger = logging.getLogger(__name__)


base_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(base_dir, 'config.json')

with open(config_path, "r") as f:
    config = json.load(f)

mech_eye = TriggerWithExternalDeviceAndFixedRate(vel_mul=config["vel_mul"])
robot = mech_eye.robot


def handle_errors(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.exception(f"Error in '{func.__name__}': {e}")
            # Move robot to safe position
            if read_current_point_index()<=32:
                robot.MoveCart(p90, 0, 0, vel=config["vel_mul"] * 50)
            else:
                robot.MoveCart(p91, 0, 0, vel=config["vel_mul"] * 50)
            robot.WaitMs(500)
            # mech_eye.profiler.disconnect()
            # robot.WaitMs(500)
            # robot.SetDO(7, 0)  # Set DO7 to 0 (vacuum off)
            # robot.WaitMs(500)
            logger.error("Robot moved to safe position due to error.")
            # # Get the scanner instance and restart the cycle
            # scanner = args[0]  # assuming first argument is self
            # scanner.run_scan_cycle()  # restart the scanning cycle
            
    return wrapper


def read_current_point_index() -> int:
    file_path = os.path.join(base_dir, "point_index.txt")
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            return int(file.read().strip())
    return 0


def write_current_point_index(index: int):
    file_path = os.path.join(base_dir, "point_index.txt")
    with open(file_path, 'w') as file:
        file.write(str(index))

def is_mysql_available() -> bool:
    try:
        conn = mysql.connector.connect(
            host="192.168.1.180",
            user="cobot_dbuser",
            password="um6vv$7*sJ@5Q*",
            database="cobot",
            connection_timeout=2  # hızlıca timeout versin
        )
        conn.close()
        return True
    except mysql.connector.Error:
        return False

# Add save_figures configuration if not present
if "save_figures" not in config:
    config["save_figures"] = True
    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)
        
def save_figure(plt, filename: str, dpi: int = 300):
    """Helper function to save matplotlib figures"""
    if config["save_figures"]:
        fig_path = os.path.join(os.path.dirname(__file__), "Scan_Outputs", "figures", filename)
        os.makedirs(os.path.dirname(fig_path), exist_ok=True)
        plt.savefig(fig_path, dpi=dpi, bbox_inches='tight')
        logger.info(f"Plot saved to {fig_path}")

# Backend configuration: Agg mode is non-interactive; TkAgg is interactive.
if config["use_agg"]:
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.show = lambda: None
else:
    matplotlib.use('TkAgg')
    import matplotlib.pyplot as plt

class JaguarScanner:
    """
    JaguarScanner class; a professional application that manages self.robot control, scanning, and measurement operations.
    
    Features:
      - Collects, processes, and saves measurement data to an Excel file.
      - Manages the robot's pick and put-back operations.
      - Increases performance with threaded computation.
    """
    def __init__(self, vel_mul: float=1, use_agg: bool = config["use_agg"], put_back: bool = False):
        """
        Initializes a JaguarScanner instance.
        
        Args:
            vel_mul (float): Velocity multiplier.
            use_agg (bool, optional): Use Agg mode. Default is True.
            put_back (bool, optional): Whether the part will be put back. If False, it is directed to the trash point.
        """
        self.mech_eye = TriggerWithExternalDeviceAndFixedRate(vel_mul)
        self.robot = self.mech_eye.robot
        self.pcd = o3d.geometry.PointCloud()
        self.results = []
        self.old_point = None
        self.excel_threads = []
        self.points = left_of_robot_points + left_small + right_of_robot_points + right_small
        self.pick_point = 1
        self.robot_tcp = [0, 0, 0, 0, 0, 0]
        self.sio = socketio.Client()
        self.current_di0_value = 0
        self.di0_thread = threading.Thread(target=self.read_di0_updates, daemon=True)
        self.di0_thread.start()
        self.rescan = 0
        self.db_writer = AppwriteDataWriter()
        

    def read_di0_updates(self):
        sio = self.sio
        @sio.event
        def connect():
            print("Connected to Socket.IO server!")

        @sio.event
        def robot_status(data):
            self.robot_tcp = data.get("TCP", None)
            self.current_di0_value = data.get("DI0", 0)
            # logger.error(f"DI0 updated: {self.current_di0_value}")
            # logger.error(f"Robot TCP: {self.robot_tcp}")

        try:
            sio.connect('http://localhost:5000')
            sio.wait()
        except Exception as e:
            logger.error(f"Bağlantı hatası: {e}")

    @staticmethod
    def send_feedback():
        try:
            url = f"http://{DEVICE_IP}:{PORT}/api/scan"
            payload = {"message": "FORCE_RESTART"}
            
            # Add timeout
            response = requests.post(url, json=payload, timeout=5)
            
            if response.status_code == 200:
                logger.info(f"Feedback sent successfully: {response.json()}")
                return True
            else:
                logger.error(f"Feedback failed. Code: {response.status_code}, Response: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error: {e}")
            return False
        except Exception as e:
            logger.error(f"General error: {e}")
            return False

    @staticmethod
    def rotate_point_cloud(points: np.ndarray, angle_degrees: float, axis: str) -> np.ndarray:
        angle_radians = np.radians(angle_degrees)
        if axis == "z":
            rotation_matrix = np.array([
                [np.cos(angle_radians), -np.sin(angle_radians), 0],
                [np.sin(angle_radians),  np.cos(angle_radians), 0],
                [0, 0, 1]
            ])
        elif axis == "x":
            rotation_matrix = np.array([
                [1, 0, 0],
                [0, np.cos(angle_radians), -np.sin(angle_radians)],
                [0, np.sin(angle_radians),  np.cos(angle_radians)]
            ])
        elif axis == "y":
            rotation_matrix = np.array([
                [np.cos(angle_radians), 0, np.sin(angle_radians)],
                [0, 1, 0],
                [-np.sin(angle_radians), 0, np.cos(angle_radians)]
            ])
        else:
            raise ValueError("Desteklenmeyen eksen. 'x', 'y' veya 'z' girin.")
        return points @ rotation_matrix.T

    @staticmethod
    def to_origin(points: np.ndarray) -> np.ndarray:
        min_x, min_y = np.min(points[:, 0]), np.min(points[:, 1])
        points[:, 0] -= min_x
        points[:, 1] -= min_y
        return points

    @staticmethod
    def remove_gripper_points(points: np.ndarray) -> np.ndarray:
        min_x = np.min(points[:, 0])
        y_candidates = points[:, 1][points[:, 0] < min_x + 23]
        y_min, y_max = np.min(y_candidates), np.max(y_candidates)
        return points[(points[:, 1] < y_min) | (points[:, 1] > y_max)]

    def get_next_valid_index(self, current_index: int, total_points: int) -> int:
        with open(config_path, 'r') as file:
            config = json.load(file)
            ignored = config.get('ignored_points', [])
        next_index = (current_index + 1) % total_points
        while ignored and next_index in ignored:
            next_index = (next_index + 1) % total_points
        return next_index

    def write_to_sqlite(self, result, iteration, group_number):
        self.db_writer.write_to_sqlite(result, iteration, group_number)

    def is_database_available(self) -> bool:
        return self.db_writer.is_appwrite_available()

    def get_current_group_info(self):
        return self.db_writer.get_current_group_info()

    def write_to_db(self, result: dict, iteration: int, group_number: int):
        self.db_writer.write_to_db(result, iteration, group_number)

    def check_part_quality(self, results: dict) -> int:
        for feature, target_tolerance in config["tolerances"].items():
            target, tolerance = target_tolerance
            value = results.get(feature, None)
            
            if value is None:
                print(f"Parça kalite kontrolünden geçemedi: {feature} değeri hesaplanamadı")
                return False

            lower_bound = target - tolerance
            upper_bound = target + tolerance
            
            if not (lower_bound <= value <= upper_bound):
                deviation = abs(value - target)
                print(f"Parça kalite kontrolünden geçemedi: {feature} = {value}, hedef = {target}±{tolerance}")
                
                # Gürültüden kaynaklı olabilir mi kontrolü (örneğin toleransın 2 katından fazla sapma varsa)
                if deviation > tolerance * 2:
                    
                    logger.error(f"⚠ Uyarı: {feature} ölçümünde olasılıkla gürültü kaynaklı anormal bir değer algılandı.")
                    return deviation
                
                return False

        print("Parça kalite kontrolünden başarıyla geçti.")
        return True

    def pick_object(self, point: dict, soft_point):
        """
        Performs the pick operation.
        
        Args:
            point (dict): Target point.
            soft_point: Soft point position.
            use_left_transit_point (bool): Whether to use back transit.
        """
        transit_vel = 80
        if self.cycle == 0:
            self.robot.Mode(1)  # Set robot to manual mode so it moves slower on the first movement

        # Special case: Extra transit movements at certain points
        if point == right_of_robot_points[0]:
            transit_vel = 50
            self.robot.MoveCart(p90, 0, 0, vel=config["vel_mul"] * transit_vel)
        elif point == left_of_robot_points[0]:
            transit_vel = 50
            self.robot.MoveCart(p91, 0, 0, vel=config["vel_mul"] * transit_vel)

        self.robot.MoveCart(soft_point, 0, 0, vel=config["vel_mul"] * 100)
        self.robot.Mode(0)  # Set robot to automatic mode

        # Transit movements
        if point in (right_of_robot_points + right_small) and point["p_up"][0] > 300:
            transit_vel = 50
            self.robot.MoveCart(right_transit_point, 0, 0, vel=config["vel_mul"] * transit_vel)
        elif point in (left_of_robot_points+left_small) and (point["p_up"][0] > 300 and point in left_of_robot_points):
            transit_vel = 50
            self.robot.MoveCart(left_transit_point, 0, 0, vel=config["vel_mul"] * transit_vel)
        
        # Pick movements
        self.robot.MoveCart(point["p_up"], 0, 0, vel=config["vel_mul"] * transit_vel)
        self.robot.MoveL(point["p"], 0, 0, vel=config["vel_mul"] * 50)
        self.robot.WaitMs(1000)
        self.robot.SetDO(7, 1)  # Signal to grip the part
        print("PICK OBJECT", self.current_di0_value)
        
        # Check if the pick operation was successful according to the DI0 value
        if not self.current_di0_value:
            print("Part successfully gripped.")
            self.robot.Mode(0)
        elif self.current_di0_value == 1:
            start_time = time.time()
            while self.current_di0_value == 1 and (time.time() - start_time) < 5:
                if (time.time() - start_time)%2 == 0:
                    logger.error("Part gripping error, waiting...")
                time.sleep(0.1) 
            if self.current_di0_value == 1:
                # In case of part gripping error
                self.robot.SetDO(7, 0)
                print("Part gripping error.")
                self.robot.Mode(1)
                # Update index for new pick attempt
                current_index = read_current_point_index()
                current_index = self.get_next_valid_index(current_index, len(self.points))
                self.robot.MoveL(point["p_up"], 0, 0, vel=config["vel_mul"] * transit_vel)
                write_current_point_index(current_index)
                
                # Prepare for new pick operation
                point = self.points[current_index]
                if current_index < len(left_of_robot_points + left_small):
                    soft_point = p90
                else:
                    soft_point = p91
                
                if config["same_place_index"]!= -1:
                    point = self.points[config["same_place_index"]]
                else:
                    point = self.points[current_index]
                    
                self.pick_point = point
                self.pick_soft_point = soft_point
                self.pick_left_transit_point = left_transit_point
                self.pick_object(point, soft_point)
                return
            else:
                print("Part successfully gripped.")
                self.robot.Mode(0)
        
        self.robot.WaitMs(1500)
        self.robot.MoveL(point["p_up"], 0, 0, vel=config["vel_mul"] * transit_vel)
        # Return transit movements
        if point in (right_of_robot_points + right_small) and point["p_up"][0] > 300:
            transit_vel = 50
            self.robot.MoveCart(right_transit_point, 0, 0, vel=config["vel_mul"] * transit_vel)
        elif point in (left_of_robot_points+left_small) and (point["p_up"][0] > 300 and point in left_of_robot_points):
            transit_vel = 50
            self.robot.MoveCart(left_transit_point, 0, 0, vel=config["vel_mul"] * transit_vel)
        
        # Final movement: go to soft point
        self.robot.MoveCart(soft_point, 0, 0, vel=config["vel_mul"] * transit_vel)
    
    @handle_errors
    def smol_calc(self, small_data: np.ndarray):
        # Rotate, filter, and move the point cloud to the origin reference
        small = self.rotate_point_cloud(small_data, -90, "z")
        small = small[small[:, 2] > np.min(small[:, 2]) + 37]
        small = small[small[:, 0] < np.min(small[:, 0]) + 50]
        small = self.to_origin(small)
        if config["save_point_clouds"]:
            self.pcd.points = o3d.utility.Vector3dVector(small)
            out_path = os.path.join(os.path.dirname(__file__), "Scan_Outputs", "small.ply")
            o3d.io.write_point_cloud(out_path, self.pcd)
            logger.info(f"Small point cloud saved to {out_path}")
        # raw_small = small.copy()
        # self.l_40 = get_40(raw_small)
        circle_fitter = CircleFitter(small)
        # If needed, try/except can be used for parameters that may cause errors.
        _, z_center_small, radius_small = circle_fitter.fit_circles_and_plot(
            find_second_circle=False, val_x=0.175, val_z=0.195, delta_z=23,clc_metrics=True,name="SMALL"
        )
        # Save the plot before getting other measurements
        save_figure(plt, "small_circles.png")
        
        s_datum = circle_fitter.get_datum()
        self.dist_3mm_s, _ = circle_fitter.get_distance(second_crc=False, z_distance_to_datum=23.1)
        self.feature_3 = z_center_small - s_datum
        self.radius_small = radius_small
        self.z_center_small = z_center_small
        
        if config["use_agg"]:
            plt.close()
        elif not config["use_agg"]:
            plt.show()
            
        logger.debug("smol_calc completed successfully.")

    @handle_errors
    def hor_calc(self, horizontal_data: np.ndarray, horizontal2_data: np.ndarray):
        # First, we make corrections on horizontal2_data
        horizontal2_data[:, 2] -= 70
        horizontal2_data[:, 0] -= 50.21

        if config["save_point_clouds"]:
            out_path2 = os.path.join(os.path.dirname(__file__), "Scan_Outputs", "horizontal2.ply")
            self.pcd.points = o3d.utility.Vector3dVector(horizontal2_data)
            o3d.io.write_point_cloud(out_path2, self.pcd)
            logger.info(f"Horizontal2 point cloud saved to {out_path2}")

            out_path_pre = os.path.join(os.path.dirname(__file__), "Scan_Outputs", "horizontal_pre.ply")
            self.pcd.points = o3d.utility.Vector3dVector(horizontal_data)
            o3d.io.write_point_cloud(out_path_pre, self.pcd)
            logger.info(f"Horizontal pre point cloud saved to {out_path_pre}")

        # Datum calculation
        diff = np.abs(np.max(horizontal_data[:, 0]) - np.min(horizontal2_data[:, 0]))
        datum_horizontal = np.max(horizontal_data[:, 0]) - diff

        # Create line points and merge with point cloud
        y_values = np.linspace(np.min(horizontal_data[:, 1]), np.max(horizontal_data[:, 1]), num=100)
        line_points = np.array([[datum_horizontal, y, np.min(horizontal_data[:, 2])] for y in y_values])
        augmented_pc = np.vstack((horizontal_data, line_points))
        horizontal = self.rotate_point_cloud(augmented_pc, 90, "z")
        horizontal = self.to_origin(horizontal)
        self.horizontal = horizontal

        if config["save_point_clouds"]:
            out_path_post = os.path.join(os.path.dirname(__file__), "Scan_Outputs", "horizontal_post.ply")
            self.pcd.points = o3d.utility.Vector3dVector(horizontal)
            o3d.io.write_point_cloud(out_path_post, self.pcd)
            logger.info(f"Horizontal post point cloud saved to {out_path_post}")

        self.circle_fitter = CircleFitter(horizontal)
        _, circle2 = self.circle_fitter.fit_circles_and_plot(clc_metrics=True,name="HORIZONTAL")
        # Save the plot before getting other measurements
        save_figure(plt, "horizontal_circles.png")
        
        self.dist_3mm_h = self.circle_fitter.get_distance()[0]
        self.height = np.max(self.horizontal[:, 1]) - self.circle_fitter.get_datum()
        self.feature_1 = circle2[1]
        self.feature_2 = circle2[2]
        
        if config["use_agg"]:
            plt.close()
        elif not config["use_agg"]:
            plt.show()
            
        logger.debug("hor_calc completed successfully.")

    @handle_errors
    def process_vertical_measurement(self, vertical_data: np.ndarray):
        # Process vertical data
        vertical = self.remove_gripper_points(vertical_data)
        vertical = self.rotate_point_cloud(vertical, 180, "z")

        if config["save_point_clouds"]:
            out_path_vertical = os.path.join(os.path.dirname(__file__), "Scan_Outputs", "vertical.ply")
            pcd = o3d.geometry.PointCloud()
            pcd.points = o3d.utility.Vector3dVector(vertical)
            o3d.io.write_point_cloud(out_path_vertical, pcd)
            logger.info(f"Vertical point cloud saved to {out_path_vertical}")
        
        vertical_copy = self.to_origin(vertical.copy())
        self.l_40 = get_40(vertical_copy)
        l_17_2, ok_17_2 = horn_diff(vertical_copy)
        save_figure(plt, "vertical_horn_17_2.png")
        if not config["use_agg"]:
            plt.show()
        plt.close()
        
        l_23_4, ok_23_4 = horn_diff(vertical_copy, 240, 280)
        save_figure(plt, "vertical_horn_23_4.png")
        if not config["use_agg"]:
            plt.show()
        plt.close()
        
        # Result calculations
        B = self.circle_fitter.get_B()
        b_trans_val = np.max(vertical[:, 1]) - np.max(self.horizontal[:, 2])
        b_vertical = B + b_trans_val
        _, _, r1, l_79_73 = slope(vertical, b_vertical)
        save_figure(plt, "vertical_slope_1.png")
        if not config["use_agg"]:
            plt.show()
        plt.close()
        
        _, _, r2, _ = slope(vertical, y_divisor=0.11, crc_l=28)
        save_figure(plt, "vertical_slope_2.png")
        if not config["use_agg"]:
            plt.show()
        plt.close()
        
        l_42 = np.max(vertical[:, 1]) - b_vertical
        l_248 = arm_horn_lengths(vertical, b_vertical)
        mean_3mm = np.mean([self.dist_3mm_h, self.dist_3mm_s])
        
        l_81_5,l_7_1 = filter_and_visualize_projection_with_ply(self.horizontal)
        l_88_6 = l_81_5 + l_7_1
        save_figure(plt, "vertical_projection.png")
        if not config["use_agg"]:
            plt.show()
        plt.close()

        vertical_results = {
            "l_17_2": l_17_2,
            "l_23_4": l_23_4,
            "l_42": l_42,
            "l_79_73": l_79_73,
            "l_248": l_248,
            "r1": (r1 - self.feature_2),
            "r2": (r2 + self.feature_2),
            "feature_1": self.feature_1,
            "mean_3mm": mean_3mm,
            "l_88_6": l_88_6,
            "l_81_5": l_81_5,
            "ok_17_2": ok_17_2
        }

        current_results = self.combine_results(vertical_results)
        logger.debug("Vertical measurements processed successfully.")
        return current_results

    def pick_tape(self):
        self.robot.SetDO(1, 1)      # mainflow on
        self.robot.SetDO(0, 0)      # Piston off
        time.sleep(3)
        self.robot.SetDO(5, 0)      # Rail open
        self.robot.SetDO(2, 1)      # Rail closed
        time.sleep(2)
        self.robot.SetDO(0, 1)      # Piston on
        time.sleep(1)
        self.robot.SetDO(3, 1)      # Vacuum on
        time.sleep(2)
        self.robot.SetDO(0, 0)      # Piston off
        time.sleep(4)
        self.robot.SetDO(2, 0)
        self.robot.SetDO(5, 1)      
        time.sleep(2)

    def after_scan(self,quality_check: int):

        # Part drop operations
        if config["pick"]:
            logger.error("Part drop operation started.")
            if config["drop_object"]:
                #Check whether the part quality is acceptable according to that drop it to metal detector or trash if put_back is False
                if quality_check == 1:
                    drop_point = metal_detector
                    logger.info("Part passed quality control, dropping to metal detector.")
                else:
                    drop_point = trash
                    logger.error("Part failed quality control, dropping to trash instead of metal detector.")

                if config["put_back"] and drop_point == trash:
                    point = self.pick_point
                    soft_point = self.pick_soft_point
                    transit_vel = 60

                    self.robot.MoveCart(soft_point, 0, 0, vel=config["vel_mul"] * 100)
                    if point in right_of_robot_points and point["p_up"][0] > 300:
                        self.robot.MoveCart(right_transit_point, 0, 0, vel=config["vel_mul"] * transit_vel)
                    elif (point["p_up"][0] > 300) and (point in (left_of_robot_points+left_small)):
                        transit_vel = 50
                        self.robot.MoveCart(left_transit_point, 0, 0, vel=config["vel_mul"] * transit_vel)
                    
                    self.robot.MoveCart(point["p_up"], 0, 0, vel=config["vel_mul"] * transit_vel)
                    self.robot.MoveL(point["p"], 0, 0, vel=config["vel_mul"] * 50)
                    self.robot.WaitMs(500)
                    self.robot.SetDO(7, 0)
                    self.robot.WaitMs(1000)
                    self.robot.MoveL(point["p_up"], 0, 0, vel=config["vel_mul"] * transit_vel)
                    
                    if point in right_of_robot_points and point["p_up"][0] > 300:
                        self.robot.MoveCart(right_transit_point, 0, 0, vel=config["vel_mul"] * transit_vel)
                    elif (point["p_up"][0] > 300) and (point in (left_of_robot_points+left_small)):
                        transit_vel = 50
                        self.robot.MoveCart(left_transit_point, 0, 0, vel=config["vel_mul"] * transit_vel)

                else: # If put_back is false or drop point is not trash, take the part to the band station and drop it at the metal_detector point
                    logger.error("Going to band station.")
                    self.robot.MoveL(p91, 0, 0, vel=config["vel_mul"] * 35)
                    # Piston and vacuum control steps for dropping to metal detector
                    
                    self.robot.SetDO(1, 1)      # mainflow on
                    self.robot.SetDO(0, 0)      # Piston off
                    self.robot.WaitMs(3000)
                    self.robot.SetDO(5, 0)      # Rail open
                    self.robot.SetDO(2, 1)      # Rail closed
                    self.robot.WaitMs(2000)
                    self.robot.SetDO(0, 1)      # Piston on
                    self.robot.WaitMs(1000)
                    self.robot.SetDO(3, 1)      # Vacuum on
                    self.robot.WaitMs(2000)
                    self.robot.SetDO(0, 0)      # Piston off
                    self.robot.WaitMs(4000)
                    self.robot.SetDO(2, 0)
                    self.robot.SetDO(5, 1)      
                    self.robot.WaitMs(2000)
                    self.robot.MoveL(p91, 0, 0, vel=config["vel_mul"] * 35)
                    self.robot.MoveL(prepreplace, 0, 0, vel=config["vel_mul"] * 35)
                    self.robot.MoveL(preplace, 0, 0, vel=config["vel_mul"] * 35)
                    self.robot.MoveL(place, 0, 0, vel=config["vel_mul"] * 10)
                    self.robot.SetDO(7, 0)      # Drop the part
                    self.robot.WaitMs(1000)
                    self.robot.MoveL(safeback, 0, 0, vel=config["vel_mul"] * 35)
                    self.robot.WaitMs(1000)
                    self.robot.SetDO(0, 1)      # Piston on
                    self.robot.WaitMs(2000)
                    self.robot.SetDO(3, 0)      # Vacuum off (piston vacuum)
                    self.robot.WaitMs(1000)
                    self.robot.SetDO(0, 0)      # Piston off
                    self.robot.WaitMs(3000)
                    self.robot.SetDO(5, 0)      # Rail open
                    self.robot.SetDO(2, 1)      # Rail closed
                    self.robot.MoveL(place, 0, 0, vel=config["vel_mul"] * 20)
                    self.robot.WaitMs(1000)
                    self.robot.SetDO(7, 1)
                    self.robot.WaitMs(1000)
                    self.robot.MoveL(preplace, 0, 0, vel=config["vel_mul"] * 10)
                    self.robot.MoveL(prepreplace, 0, 0, vel=config["vel_mul"] * 35)
                    self.robot.MoveL(p91, 0, 0, vel=config["vel_mul"] * 35)
                    self.robot.WaitMs(500)
                    self.robot.MoveL(p90, 0, 0, vel=config["vel_mul"] * 35)    
                    self.robot.MoveCart(metal_detector, 0, 0, vel=config["vel_mul"] * 35)
                    self.robot.MoveCart(post_metal_detector, 0, 0, vel=config["vel_mul"] * 35)
                    self.robot.WaitMs(500)
                    self.robot.SetDO(7, 0)
                    self.robot.WaitMs(500)
                    self.robot.MoveCart(metal_detector, 0, 0, vel=config["vel_mul"] * 35)
                    self.robot.MoveCart(p90, 0, 0, vel=config["vel_mul"] * 35)    
                    self.robot.MoveL(p91, 0, 0, vel=config["vel_mul"] * 35)

                    logger.error("Object dropped at appropriate drop point.")
            elif config["put_back"] :
                point = self.pick_point
                soft_point = self.pick_soft_point
                transit_vel = 60

                self.robot.MoveCart(soft_point, 0, 0, vel=config["vel_mul"] * 60)
                if point in right_of_robot_points and point["p_up"][0] > 300:
                    self.robot.MoveCart(right_transit_point, 0, 0, vel=config["vel_mul"] * transit_vel)
                elif (point["p_up"][0] > 300) and (point in (left_of_robot_points+left_small)):
                    transit_vel = 50
                    self.robot.MoveCart(left_transit_point, 0, 0, vel=config["vel_mul"] * transit_vel)
                
                self.robot.MoveCart(point["p_up"], 0, 0, vel=config["vel_mul"] * transit_vel)
                self.robot.MoveL(point["p"], 0, 0, vel=config["vel_mul"] * 50)
                self.robot.WaitMs(500)
                self.robot.SetDO(7, 0)
                self.robot.WaitMs(1500)
                self.robot.MoveL(point["p_up"], 0, 0, vel=config["vel_mul"] * transit_vel)
                
                if point in right_of_robot_points and point["p_up"][0] > 300:
                    self.robot.MoveCart(right_transit_point, 0, 0, vel=config["vel_mul"] * transit_vel)
                elif (point["p_up"][0] > 300) and (point in (left_of_robot_points+left_small)):
                    transit_vel = 50
                    self.robot.MoveCart(left_transit_point, 0, 0, vel=config["vel_mul"] * transit_vel)
            else:
                logger.info("Part drop setting disabled.")

    def combine_results(self, vertical_results: dict) -> dict:
        # Helper function to safely get values
        def safe_get(dict_obj, key, default=None):
            value = dict_obj.get(key, default)
            # If a value is a dictionary, convert to string representation
            if isinstance(value, dict):
                # print(f"Warning: Dictionary value detected for {key}: {value}")
                return str(value)
            return value
        
        results = {
            "Feature1 (102.1)": safe_get(vertical_results, "feature_1", self.feature_1),
            "Feature2 (25mm/2)": self.feature_2,
            "Feature3 (23.1)": self.feature_3,
            "Feature4 (25mm/2)": self.radius_small,
            "Feature5 (L40)": self.l_40,
            "Feature6 (L248)": safe_get(vertical_results, "l_248"),
            "Feature7 (L42)": safe_get(vertical_results, "l_42"),
            "Feature8 (L79.73)": safe_get(vertical_results, "l_79_73"),
            "Feature9 (R1-50)": safe_get(vertical_results, "r1"),
            "Feature10 (R2-35)": safe_get(vertical_results, "r2"),
            "Feature11 (3mm)": safe_get(vertical_results, "mean_3mm"),
            "Feature12 (88.6)": safe_get(vertical_results, "l_88_6"),
            "Feature13 (10.6)": self.feature_3 - self.radius_small,
            "Feature14 (81.5)": safe_get(vertical_results, "l_81_5"),
            "Feature15 (L23.4)": safe_get(vertical_results, "l_23_4"),
            "Feature16 (L17.2)": safe_get(vertical_results, "l_17_2"),
            "Feature17 (2C)": safe_get(vertical_results, "ok_17_2")
        }
        
        # Ensure all values are serializable
        for key, value in results.items():
            try:
                # For testing, json.dumps
                json.dumps(value)
            except (TypeError, OverflowError):
                # print(f"Non-serializable value found: {key} = {value}")
                results[key] = str(value)
        
        return results

    def run_scan_cycle(self):
        ROBOT_POSITIONS = config["robot_positions"]

        # Başlangıçta grup bilgilerini çek
        self.current_group, self.group_indices = self.get_current_group_info()

        if self.robot_tcp[0] >= 300:
            if self.robot_tcp[1] >= 0:
                logger.error("Robot is on the right side", self.robot_tcp[0])
                self.robot.MoveCart(right_transit_point, 0, 0, vel=config["vel_mul"] * 60)
                self.robot.MoveCart(p91, 0, 0, vel=config["vel_mul"] * 60)
            else:
                logger.error("Robot is on the left side", self.robot_tcp[0])
                self.robot.MoveCart(left_transit_point, 0, 0, vel=config["vel_mul"] * 60)
                self.robot.MoveCart(p90, 0, 0, vel=config["vel_mul"] * 60)
        
        self.cycle = 0
        while self.cycle < config["range_"]:
            start_time = time.time()
            current_results = {}
            selected_results = {}  # Initialize selected_results
            
            # Her cycle için deneme verilerini saklamak için liste
            attempt_results = []
            
            current_index = read_current_point_index()
            if current_index in config["ignored_points"]:
                current_index = self.get_next_valid_index(current_index, len(self.points))
                write_current_point_index(current_index)
            if self.cycle != 0 and self.rescan == 0:
                self.old_point = self.points[current_index]
                current_index = self.get_next_valid_index(current_index, len(self.points))
                write_current_point_index(current_index)
            
            try:
                if config["pick"] and self.rescan == 0:
                    if current_index < len(left_of_robot_points + left_small):
                        soft_point = p90
                    else:
                        soft_point = p91

                    if config["same_place_index"]!= -1:
                        point = self.points[config["same_place_index"]]
                    else:
                        point = self.points[current_index]

                    self.pick_point = point
                    self.pick_soft_point = soft_point
                    self.pick_left_transit_point = left_transit_point
                    self.pick_object(point, soft_point)
                
                self.robot.MoveCart(ROBOT_POSITIONS['scrc'], 0, 0, vel=config["vel_mul"] * 100)
                
                small_data = self.mech_eye.main(lua_name="small.lua", scan_line_count=1500)
                if config["use_agg"]:
                    thread_small = threading.Thread(target=self.smol_calc, args=(small_data,))
                    thread_small.start()
                else:
                    self.smol_calc(small_data)
                    plt.show()

                horizontal_data = self.mech_eye.main(lua_name="horizontal.lua", scan_line_count=1500)
                horizontal2_data = self.mech_eye.main(lua_name="horizontal2.lua", scan_line_count=1500)
                if config["use_agg"]:
                    thread_horizontal = threading.Thread(target=self.hor_calc, args=(horizontal_data, horizontal2_data))
                    thread_horizontal.start()
                else:
                    self.hor_calc(horizontal_data, horizontal2_data)
                    plt.show()

                vertical_data = self.mech_eye.main(lua_name="vertical.lua", scan_line_count=4000)
                plt.show()

                if config["use_agg"]:
                    thread_small.join()
                    thread_horizontal.join()

                current_results = self.process_vertical_measurement(vertical_data)
                
                # Bu deneme sonucunu sakla
                attempt_results.append(current_results.copy())
                
                quality_check_result = self.check_part_quality(current_results)
                
                # Geçerli ölçüm kontrolü (True veya False dışında değer dönerse geçersiz)
                is_valid_measurement = quality_check_result in [True, False]
                quality_check = True if quality_check_result == True else False
                
                if not is_valid_measurement:
                    if self.rescan < config["max_rescan"]:
                        self.rescan += 1
                        logger.error("Invalid measurement detected (noise). Restarting scan.")
                        continue
                    else:
                        logger.error("Max rescan attempts reached. Using last measurement...")
                elif not quality_check:
                    if self.rescan < config["max_rescan"]:
                        self.rescan += 1
                        logger.error("Quality check failed. Restarting scan.")
                        continue
                    else:
                        logger.error("Max rescan attempts reached. Continuing...")

                # Geçerli ölçümlerden son geçerli olanını seç
                valid_results = []
                for result in attempt_results:
                    test_quality = self.check_part_quality(result)
                    if test_quality in [True, False]:
                        valid_results.append(result)
                
                # Son geçerli ölçümü kullan, yoksa son ölçümü kullan
                if valid_results:
                    selected_results = valid_results[-1]  # Son geçerli ölçüm
                    final_quality_check = self.check_part_quality(selected_results) == True
                    logger.info("Using last valid measurement from attempts.")
                else:
                    selected_results = attempt_results[-1]  # Son ölçüm (geçersiz olsa da)
                    final_quality_check = False
                    logger.warning("No valid measurements found. Using last measurement.")

                self.after_scan(final_quality_check) # After scan operations

                self.rescan = 0  # Reset rescan counter after successful scan
                self.cycle += 1  # Increment cycle count

                selected_results["Index"] = read_current_point_index()
                selected_results["OK"] = "1" if final_quality_check else "0"
                
                # Grup yönetimi
                current_index = read_current_point_index()
                if current_index not in self.group_indices:
                    # Bu index bu gruba ilk kez ekleniyor
                    self.group_indices.add(current_index)
                    
                    # Eğer grup 64 index'e ulaştıysa yeni grup başlat
                    if len(self.group_indices) >= 64:
                        self.current_group += 1
                        self.group_indices = {current_index}  # Yeni grup için sadece bu index
                
                if config["save_to_db"]:
                    try:
                        logger.error("Writing results to database...")
                        self.write_to_db(selected_results, iteration=read_current_point_index(), group_number=self.current_group)
                        logger.error("Results written to database successfully.")
                    except Exception as e:
                        logger.error(f"Database write error: {e}")
                
                selected_results["Processing Time (s)"] = time.time() - start_time
                
                # Bellekteki deneme verilerini temizle
                attempt_results.clear()
                
            except Exception as e:
                current_results = {"Error": str(e)}
                selected_results = current_results
            finally:
                if config["use_agg"] == True:
                    plt.close("all")
                if "Error" in selected_results or "Index" in selected_results:
                    with open('jsons/scan_output.json', 'a') as f:
                        f.write(json.dumps(selected_results) + '\n')

if __name__ == "__main__":
    scanner = JaguarScanner(vel_mul=config["vel_mul"])
    scanner.run_scan_cycle()