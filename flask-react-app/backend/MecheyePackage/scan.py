import os
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


DEVICE_IP = os.environ.get('IP_ADDRESS')
PORT = os.environ.get('PORT')
if not DEVICE_IP or not PORT:
    raise EnvironmentError('Environment variables REACT_APP_DEVICE_IP and REACT_APP_PORT must be set')

API_BASE_URL = f"http://{DEVICE_IP}:{PORT}"
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
mech_eye = TriggerWithExternalDeviceAndFixedRate(vel_mul=1.0)
robot = mech_eye.robot

if not logger.handlers:
    logger.addHandler(handler)

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
            mech_eye.profiler.disconnect()
            robot.WaitMs(500)
            robot.SetDO(7, 0)  # Set DO7 to 0 (vacuum off)
            robot.WaitMs(500)
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

base_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(base_dir, 'config.json')
with open(config_path, "r") as f:
    config = json.load(f)

# Backend yapılandırması: Agg mod, non-interaktif; TkAgg ise interaktif.
if config["use_agg"]:
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.show = lambda: None
else:
    matplotlib.use('TkAgg')
    import matplotlib.pyplot as plt

class JaguarScanner:
    """
    JaguarScanner sınıfı; self.robot kontrolü, tarama ve ölçüm işlemlerini yürüten profesyonel bir uygulamadır.
    
    Özellikler:
      - Ölçüm verilerini toplar, işler ve Excel dosyasına kaydeder.
      - Robotun pick (parça alma) ve put-back (parça geri koyma) işlemlerini yönetir.
      - Thread'li hesaplama ile performansı artırır.
    """
    def __init__(self, vel_mul: float=1, use_agg: bool = config["use_agg"], put_back: bool = False):
        """
        JaguarScanner örneğini başlatır.
        
        Args:
            vel_mul (float): Hız çarpanı.
            use_agg (bool, optional): Agg mod kullanımı. Varsayılan True.
            put_back (bool, optional): Parçanın geri konulup konulacağı. False ise trash noktasına yönlendirilir.
        """
        self.mech_eye = TriggerWithExternalDeviceAndFixedRate(vel_mul)
        self.robot = self.mech_eye.robot
        self.pcd = o3d.geometry.PointCloud()
        self.results = []
        self.old_point = None
        self.excel_threads = []
        self.points = left_of_robot_points + left_small + right_of_robot_points + right_small
        self.pick_point = 1
        self.robot_tcp = [[0],[0, 0, 0, 0, 0, 0]]
        self.sio = socketio.Client()
        self.current_di0_value = 0
        self.di0_thread = threading.Thread(target=self.read_di0_updates, daemon=True)
        self.di0_thread.start()
    
    def read_di0_updates(self):
        sio = self.sio
        @sio.event
        def connect():
            print("Socket.IO sunucusuna bağlandı!")

        @sio.event
        def robot_status(data):
            self.robot_tcp = data.get("TCP", None)
            self.current_di0_value = data.get("DI0", 0)
            # logger.error(f"DI0 güncellendi: {self.current_di0_value}")
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
            
            # Timeout ekleyin
            response = requests.post(url, json=payload, timeout=5)
            
            if response.status_code == 200:
                logger.info(f"Feedback başarıyla gönderildi: {response.json()}")
                return True
            else:
                logger.error(f"Feedback başarısız. Kod: {response.status_code}, Yanıt: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network hatası: {e}")
            return False
        except Exception as e:
            logger.error(f"Genel hata: {e}")
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


    def pick_object(self, point: dict, soft_point):
        """
        Parça alma (pick) işlemini gerçekleştirir.
        
        Args:
            point (dict): Hedef nokta.
            soft_point: Soft nokta konumu.
            use_left_transit_point (bool): Back transit kullanılacak mı.
        """
        transit_vel = 80
        # Özel durum: Belirli noktalarda ekstra transit hareketleri
        if point == right_of_robot_points[0]:
            transit_vel = 50
            self.robot.MoveCart(p90, 0, 0, vel=config["vel_mul"] * transit_vel)
        elif point == left_of_robot_points[0]:
            transit_vel = 50
            self.robot.MoveCart(p91, 0, 0, vel=config["vel_mul"] * transit_vel)

        self.robot.MoveCart(soft_point, 0, 0, vel=config["vel_mul"] * 100)
        # Transit hareketleri
        if point in (right_of_robot_points + right_small) and point["p_up"][0] > 300:
            transit_vel = 50
            self.robot.MoveCart(right_transit_point, 0, 0, vel=config["vel_mul"] * transit_vel)
        elif point in (left_of_robot_points+left_small) and (point["p_up"][0] > 300 and point in left_of_robot_points):
            transit_vel = 50
            self.robot.MoveCart(left_transit_point, 0, 0, vel=config["vel_mul"] * transit_vel)
        
        # Parça alma hareketleri
        self.robot.MoveCart(point["p_up"], 0, 0, vel=config["vel_mul"] * transit_vel)
        self.robot.MoveL(point["p"], 0, 0, vel=config["vel_mul"] * 50)
        self.robot.WaitMs(1000)
        self.robot.SetDO(7, 1)  # Parçayı kavrama sinyali
        print("PICK OBJECT", self.current_di0_value)
        
        # DI0 değerine göre parça alma işleminin başarıyla tamamlanıp tamamlanmadığını kontrol et
        if not self.current_di0_value:
            print("Parça başarıyla kavrandı.")
            self.robot.Mode(0)
        elif self.current_di0_value == 1:
            start_time = time.time()
            while self.current_di0_value == 1 and (time.time() - start_time) < 5:
                if (time.time() - start_time)%2 == 0:
                    logger.error("Parça kavrama hatası, bekleniyor...")
                time.sleep(0.1) 
            if self.current_di0_value == 1:
                # Parça kavrama hatası durumunda
                self.robot.SetDO(7, 0)
                print("Parça kavurma hatası.")
                self.robot.Mode(1)
                # Yeni parça alma girişimi için indeksi güncelle
                current_index = read_current_point_index()
                current_index = self.get_next_valid_index(current_index, len(self.points))
                self.robot.MoveL(point["p_up"], 0, 0, vel=config["vel_mul"] * transit_vel)
                write_current_point_index(current_index)
                
                # Yeni parça alma işlemi için hazırlan
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
                print("Parça başarıyla kavrandı.")
                self.robot.Mode(0)
        
        self.robot.WaitMs(1500)
        self.robot.MoveL(point["p_up"], 0, 0, vel=config["vel_mul"] * transit_vel)
        # Geri dönüş transit hareketleri
        if point in (right_of_robot_points + right_small) and point["p_up"][0] > 300:
            transit_vel = 50
            self.robot.MoveCart(right_transit_point, 0, 0, vel=config["vel_mul"] * transit_vel)
        elif point in (left_of_robot_points+left_small) and (point["p_up"][0] > 300 and point in left_of_robot_points):
            transit_vel = 50
            self.robot.MoveCart(left_transit_point, 0, 0, vel=config["vel_mul"] * transit_vel)
        
        # Son hareket: Soft point'e git
        self.robot.MoveCart(soft_point, 0, 0, vel=config["vel_mul"] * transit_vel)
    
    @handle_errors
    def smol_calc(self, small_data: np.ndarray):
        # Nokta bulutunu döndürmek, filtrelemek ve orijin referansına çevirmek
        small = self.rotate_point_cloud(small_data, -90, "z")
        small = small[small[:, 2] > np.min(small[:, 2]) + 37]
        small = small[small[:, 0] < np.min(small[:, 0]) + 50]
        small = self.to_origin(small)

        if config["save_point_clouds"]:
            self.pcd.points = o3d.utility.Vector3dVector(small)
            out_path = os.path.join(os.path.dirname(__file__), "Scan_Outputs", "small.ply")
            o3d.io.write_point_cloud(out_path, self.pcd)
            logger.info(f"Small point cloud saved to {out_path}")

        circle_fitter = CircleFitter(small)
        # Hataya yol açabilen parametreler için gerekirse try/except kullanılabilir.
        _, z_center_small, radius_small = circle_fitter.fit_circles_and_plot(
            find_second_circle=False, val_x=0.18, val_z=0.2, delta_z=25
        )
        s_datum = circle_fitter.get_datum()
        self.dist_3mm_s, _ = circle_fitter.get_distance(second_crc=False, z_distance_to_datum=23.1)
        self.feature_3 = z_center_small - s_datum
        self.radius_small = radius_small
        self.z_center_small = z_center_small
        logger.debug("smol_calc completed successfully.")

    @handle_errors
    def hor_calc(self, horizontal_data: np.ndarray, horizontal2_data: np.ndarray):
        # Önce horizontal2_data üzerinde düzeltmeleri yapıyoruz
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

        # Datum hesaplama
        diff = np.abs(np.max(horizontal_data[:, 0]) - np.min(horizontal2_data[:, 0]))
        datum_horizontal = np.max(horizontal_data[:, 0]) - diff

        # Line noktalarını oluşturup nokta bulutu ile birleştiriyoruz
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
        _, circle2 = self.circle_fitter.fit_circles_and_plot()
        self.dist_3mm_h = self.circle_fitter.get_distance()[0]
        self.l_40 = get_40(horizontal)
        self.height = np.max(self.horizontal[:, 1]) - self.circle_fitter.get_datum()
        self.feature_1 = circle2[1]
        self.feature_2 = circle2[2]
        logger.debug("hor_calc completed successfully.")

    @handle_errors
    def process_vertical_measurement(self, vertical_data: np.ndarray) -> dict:
        # Vertical veriyi işliyoruz
        vertical = self.remove_gripper_points(vertical_data)
        vertical = self.rotate_point_cloud(vertical, 180, "z")

        if config["save_point_clouds"]:
            out_path_vertical = os.path.join(os.path.dirname(__file__), "Scan_Outputs", "vertical.ply")
            pcd = o3d.geometry.PointCloud()
            pcd.points = o3d.utility.Vector3dVector(vertical)
            o3d.io.write_point_cloud(out_path_vertical, pcd)
            logger.info(f"Vertical point cloud saved to {out_path_vertical}")
        
        vertical_copy = self.to_origin(vertical.copy())
        l_17_2, ok_17_2 = horn_diff(vertical_copy)
        l_23_4, ok_23_4 = horn_diff(vertical_copy, 240, 280)
        
        # Sonuç hesaplamaları
        B = self.circle_fitter.get_B()
        b_trans_val = np.max(vertical[:, 1]) - np.max(self.horizontal[:, 2])
        b_vertical = B + b_trans_val
        _, _, r1, l_79_73 = slope(vertical, b_vertical)
        _, _, r2, _ = slope(vertical, y_divisor=0.11, crc_l=28)
        l_42 = np.max(vertical[:, 1]) - b_vertical
        l_248 = arm_horn_lengths(vertical, b_vertical)
        mean_3mm = np.mean([self.dist_3mm_h, self.dist_3mm_s])
        l_88_6 = self.feature_1 - self.feature_2
        l_81_5 = filter_and_visualize_projection_with_ply(self.horizontal)

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

        # Parça bırakma işlemleri
        if config["pick"]:
            logger.error("Parça bırakma işlemi başlatılıyor.")
            if config["drop_object"]:
                #Check whether the part quality is acceptable according to that drop it to metal detector or trash if put_back is False
                if self.check_part_quality(current_results):
                    drop_point = metal_detector
                    logger.info("Parça kalite kontrolünden geçti, metal dedektörüne bırakılıyor.")
                else:
                    drop_point = trash
                    logger.error("Parça kalite kontrolünden geçemedi, metal dedektör yerine çöpe bırakılıyor.")
                # Eğer put_back true ise ve drop point metal_detector ise, parçayı metal dedektörüne bırak

                if False: # config["put_back"] and drop_point == trash:
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

                else: # Eğer put_back false ise veya drop point trash değil ise, parçayı bant stationa götür ve metal_detector noktasına bırak
                    logger.error("bant stationa gidiliyor.")
                    self.robot.MoveL(p91, 0, 0, vel=config["vel_mul"] * 35)
                    # Metal dedektörüne bırakma işlemi için piston ve vakum kontrol adımları
                    
                    self.robot.SetDO(1, 1)      # mainflow açık
                    self.robot.SetDO(0, 0)      # Piston kapalı
                    self.robot.WaitMs(3000)
                    self.robot.SetDO(4, 0)      # Ray açık (rail)
                    self.robot.SetDO(2, 1)      # Ray kapalı
                    self.robot.WaitMs(2000)
                    self.robot.SetDO(0, 1)      # Piston açık
                    self.robot.WaitMs(1000)
                    self.robot.SetDO(3, 1)      # Vakum açık
                    self.robot.WaitMs(2000)
                    self.robot.SetDO(0, 0)      # Piston kapalı
                    self.robot.WaitMs(4000)
                    self.robot.SetDO(2, 0)
                    self.robot.SetDO(4, 1)      
                    self.robot.WaitMs(2000)
                    self.robot.MoveL(p91, 0, 0, vel=config["vel_mul"] * 35)
                    self.robot.MoveL(prepreplace, 0, 0, vel=config["vel_mul"] * 35)
                    self.robot.MoveL(preplace, 0, 0, vel=config["vel_mul"] * 35)
                    self.robot.MoveL(place, 0, 0, vel=config["vel_mul"] * 35)
                    self.robot.SetDO(7, 0)      # Parçayı bırak
                    self.robot.WaitMs(1000)
                    self.robot.MoveL(safeback, 0, 0, vel=config["vel_mul"] * 35)
                    self.robot.WaitMs(1000)
                    self.robot.SetDO(0, 1)      # Piston açık
                    self.robot.WaitMs(2000)
                    self.robot.SetDO(3, 0)      # Vakum kapalı (piston vacuum)
                    self.robot.WaitMs(1000)
                    self.robot.SetDO(0, 0)      # Piston kapalı
                    self.robot.WaitMs(3000)
                    self.robot.SetDO(4, 0)      # Ray açık (rail)
                    self.robot.SetDO(2, 1)      # Ray kapalı
                    self.robot.MoveL(place, 0, 0, vel=config["vel_mul"] * 35)
                    self.robot.WaitMs(1000)
                    self.robot.SetDO(7, 1)
                    self.robot.WaitMs(1000)
                    self.robot.MoveL(preplace, 0, 0, vel=config["vel_mul"] * 35)
                    self.robot.MoveL(prepreplace, 0, 0, vel=config["vel_mul"] * 35)
                    self.robot.MoveL(p91, 0, 0, vel=config["vel_mul"] * 35)
                    self.robot.WaitMs(500)
                    self.robot.MoveL(p90, 0, 0, vel=config["vel_mul"] * 35)      # mainflow kapalı
                    self.robot.MoveCart(metal_detector, 0, 0, vel=config["vel_mul"] * 35)
                    self.robot.SetDO(7, 0)
                    self.robot.WaitMs(1000)
                    self.robot.MoveCart(p90, 0, 0, vel=config["vel_mul"] * 35)      # mainflow kapalı
                    self.robot.MoveL(p91, 0, 0, vel=config["vel_mul"] * 35)

                    logger.info("Object dropped at appropriate drop point.")
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
                logger.info("Parça bırakma ayarı devre dışı bırakıldı.")

        return vertical_results
    
    def check_part_quality(self, results: dict) -> bool:
        for feature, target_tolerance in config["tolerances"].items():
            target, tolerance = target_tolerance
            value = results.get(feature, None)
            if value is None:
                print(f"Parça kalite kontrolünden geçemedi: {feature} değeri hesaplanamadı")
                return False
            if not (target - tolerance <= value <= target + tolerance):
                print(f"Parça kalite kontrolünden geçemedi: {feature} = {value}, hedef = {target}±{tolerance}")
                return False
        print("Parça kalite kontrolünden başarıyla geçti.")
        return True

    def write_to_db(self, result: Dict[str, float], iteration: int):
        conn = mysql.connector.connect(
            host="192.168.1.180",
            user="cobot_dbuser",
            password="um6vv$7*sJ@5Q*",
            database="cobot"
        )
        cursor = conn.cursor()

        create_table_query = """
        CREATE TABLE IF NOT EXISTS scan_results (
            id INT AUTO_INCREMENT PRIMARY KEY,
            iteration INT,
            feature VARCHAR(255),
            value DOUBLE
        )
        """
        cursor.execute(create_table_query)
        conn.commit()

        insert_query = "INSERT INTO scan_results (iteration, feature, value) VALUES (%s, %s, %s)"

        for feature_name, raw_value in result.items():
            try:
                value_float = float(raw_value)
            except (ValueError, TypeError):
                value_float = None

            data = (iteration, feature_name, value_float)
            cursor.execute(insert_query, data)

        conn.commit()
        cursor.close()
        conn.close()

    def combine_results(self, vertical_results: dict) -> dict:
        # Değerleri güvenli bir şekilde almak için yardımcı fonksiyon
        def safe_get(dict_obj, key, default=None):
            value = dict_obj.get(key, default)
            # Eğer bir değer sözlük ise, string temsiline dönüştür
            if isinstance(value, dict):
                # print(f"Uyarı: {key} için dictionary değeri algılandı: {value}")
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
        
        # Tüm değerlerin serileştirilebilir olduğundan emin olalım
        for key, value in results.items():
            try:
                # Test amaçlı json.dumps
                json.dumps(value)
            except (TypeError, OverflowError):
                # print(f"Serileştirilemeyen değer bulundu: {key} = {value}")
                results[key] = str(value)
        
        return results

    def run_scan_cycle(self):
        ROBOT_POSITIONS = config["robot_positions"]

        if self.robot_tcp[1][0] >= 300:
            if self.robot_tcp[1][1] >= 0:
                logger.error("Robot sağ tarafta", self.robot_tcp[1][0])
                self.robot.MoveCart(p91, 0, 0, vel=config["vel_mul"] * 60)
            else:
                logger.error("Robot sol tarafta", self.robot_tcp[1][0])
                self.robot.MoveCart(p90, 0, 0, vel=config["vel_mul"] * 60)

        for self.cycle in range(config["range_"]):
            start_time = time.time()
            current_results = {}
            print("Cycle:",self.cycle)
            current_index = read_current_point_index()
            if current_index in config["ignored_points"]:
                current_index = self.get_next_valid_index(current_index, len(self.points))
                write_current_point_index(current_index)
            if self.cycle != 0:
                self.old_point = self.points[current_index]
                current_index = self.get_next_valid_index(current_index, len(self.points))
                write_current_point_index(current_index)
            
            try:
                if config["pick"]:
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

                
                vertical_results = self.process_vertical_measurement(vertical_data)
                current_results = self.combine_results(vertical_results)
                current_results["Index"] = read_current_point_index()
                current_results["OK"] = "1" if self.check_part_quality(current_results) else "0"
                if config["save_to_db"]:
                    self.write_to_db(current_results, iteration=read_current_point_index())
                current_results["Processing Time (s)"] = time.time() - start_time
                
            except Exception as e:
                current_results = {"Error": str(e)}
            finally:
                if config["use_agg"] == True:
                    plt.close("all")
                with open('jsons/scan_output.json', 'a') as f:
                    f.write(json.dumps(current_results) + '\n')
        

if __name__ == "__main__":
    scanner = JaguarScanner()
    scanner.run_scan_cycle()