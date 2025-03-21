import os
import threading
import time
import numpy as np
import open3d as o3d
import pandas as pd
import mysql.connector
import matplotlib
from tkinter.messagebox import showerror
from openpyxl.styles import PatternFill
from robot_control import send_command
from Measure.Scripts import *
from mecheye_trigger import TriggerWithExternalDeviceAndFixedRate, robot
from points import *
from config import config
import sys
import json

# Backend yapılandırması: Agg mod, non-interaktif; TkAgg ise interaktif.
USE_AGG = True
if USE_AGG:
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    # Agg modda GUI gösterimleri kapatılıyor
    plt.show = lambda: None
else:
    matplotlib.use('TkAgg')
    import matplotlib.pyplot as plt


class JaguarScanner:
    """
    JaguarScanner sınıfı; robot kontrolü, tarama ve ölçüm işlemlerini yürüten profesyonel bir uygulamadır.
    
    Özellikler:
      - Ölçüm verilerini toplar, işler ve Excel dosyasına kaydeder.
      - Robotun pick (parça alma) ve put-back (parça geri koyma) işlemlerini yönetir.
      - Thread'li hesaplama ile performansı artırır.
    """
    def __init__(self, vel_mul: float, use_agg: bool = USE_AGG, put_back: bool = True):
        """
        JaguarScanner örneğini başlatır.
        
        Args:
            vel_mul (float): Hız çarpanı.
            use_agg (bool, optional): Agg mod kullanımı. Varsayılan True.
            put_back (bool, optional): Parçanın geri konulup konulmayacağı. False ise trash noktasına yönlendirilir.
        """
        self.config = config
        
        self.mech_eye = TriggerWithExternalDeviceAndFixedRate(vel_mul)
        self.pcd = o3d.geometry.PointCloud()
        self.results = []
        self.excel_threads = []
        self.points = left_of_robot_points + left_small + back_points + right_of_robot_points + right_small
        
        self.current_di0_value = (0, 0)  # Initialize with default value
        self.di0_thread = threading.Thread(target=self.read_di0_updates, daemon=True)
        self.di0_thread.start()
        
        self.tolerances = {
            "Feature1 (102.1)": (102.1, 2.0),
            "Feature2 (25mm/2)": (12.5, 0.5),
            "Feature3 (23.1)": (23.1, 1),
            "Feature4 (25mm/2)": (12.5, 0.5),
            "Feature5 (L40)": (40.0, 1),
            "Feature6 (L248)": (248.0, 2.0),
            "Feature7 (L42)": (42.0, 1.5),
            "Feature8 (L79.73)": (79.73, 1.5),
            "Feature9 (R1-50)": (50, 1.5),
            "Feature10 (R2-35)": (35, 1.5),
            "Feature11 (3mm)": (0, 3.0),
            "Feature12 (88.6)": (88.6, 1.5),
            "Feature13 (10.6)": (10.6, 1.0),
            "Feature14 (81.5)": (81.5, 1.5),
            "Feature15 (L23.4)": (23.4, 1.0),
            "Feature16 (L17.2)": (17.2, 1.0),
            "Feature17 (2C)": (0.0, 2.0)
        }

    @staticmethod
    def rotate_point_cloud(points: np.ndarray, angle_degrees: float, axis: str) -> np.ndarray:
        """
        Nokta bulutunu belirtilen eksende döndürür.
        
        Args:
            points (np.ndarray): Nokta bulutu.
            angle_degrees (float): Döndürme açısı (derece cinsinden).
            axis (str): Döndürme ekseni ('x', 'y' veya 'z').
        
        Returns:
            np.ndarray: Döndürülmüş nokta bulutu.
        """
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
        """
        Nokta bulutunu orijine taşır.
        
        Args:
            points (np.ndarray): Nokta bulutu.
            
        Returns:
            np.ndarray: Orijine taşınmış nokta bulutu.
        """
        min_x, min_y = np.min(points[:, 0]), np.min(points[:, 1])
        points[:, 0] -= min_x
        points[:, 1] -= min_y
        return points

    @staticmethod
    def remove_gripper_points(points: np.ndarray) -> np.ndarray:
        """
        Gripper bölgesindeki noktaları filtreler.
        
        Args:
            points (np.ndarray): Nokta bulutu.
            
        Returns:
            np.ndarray: Filtrelenmiş nokta bulutu.
        """
        min_x = np.min(points[:, 0])
        y_candidates = points[:, 1][points[:, 0] < min_x + 23]
        y_min, y_max = np.min(y_candidates), np.max(y_candidates)
        return points[(points[:, 1] < y_min) | (points[:, 1] > y_max)]
     
    # Function to continuously read DI0 updates from stdin
    def read_di0_updates(self):
        global current_di0_value  # Make this a global variable in your scan.py
        
        for line in sys.stdin:
            print("")  # Add an empty line for logging clarity
            try:
                # Strip whitespace and replace single quotes with double quotes for proper JSON
                clean_line = line.strip().replace("'", '"')
                print(f"Processing line: {clean_line}")
                
                data = json.loads(clean_line)
                if 'DI0' in data:
                    # Convert the JSON array back to a tuple if needed
                    di0_array = data['DI0']
                    self.current_di0_value = (di0_array[0], di0_array[1])
                    self.mech_eye.current_di0_value = self.current_di0_value
                    print(f"Received DI0 update: {self.current_di0_value}")
            except json.JSONDecodeError as e:
                print(f"Error parsing input: {line}")
                print(f"JSON error: {str(e)}")
            except Exception as e:
                print(f"Error processing input: {e}")
    
    def get_next_valid_index(self, current_index: int, ignored: list, total_points: int) -> int:
        """
        Geçerli indeksten sonraki, ignored listesinde olmayan geçerli indeksi döndürür.
        
        Args:
            current_index (int): Şu anki indeks.
            ignored (list): Yoksayılan indeksler.
            total_points (int): Toplam nokta sayısı.
            
        Returns:
            int: Geçerli sonraki indeks.
        """
        next_index = (current_index + 1) % total_points
        while ignored and next_index in ignored:
            next_index = (next_index + 1) % total_points
        return next_index

    def read_current_point_index(self) -> int:
        """
        Nokta indeksini dosyadan okur.
        
        Returns:
            int: Okunan indeks; dosya yoksa 0.
        """
        if os.path.exists(self.config.file_path):
            with open(self.config.file_path, 'r') as file:
                return int(file.read().strip())
        return 0

    def write_current_point_index(self, index: int):
        """
        Nokta indeksini dosyaya yazar.
        
        Args:
            index (int): Yazılacak indeks.
        """
        with open(self.config.file_path, 'w') as file:
            file.write(str(index))

    def pick_object(self, point: dict, soft_point, use_back_transit: bool):
        """
        Parça alma (pick) işlemini gerçekleştirir.
        
        Args:
            point (dict): Hedef nokta.
            soft_point: Soft nokta konumu.
            use_back_transit (bool): Back transit kullanılacak mı.
        """
        transit_vel = 80  # Varsayılan transit hızı

        # Özel durum: Belirli noktalarda ekstra transit hareketleri
        if point == right_of_robot_points[0]:
            transit_vel = 50
            robot.MoveCart(p90, 0, 0, vel=self.config.vel_mul * transit_vel)
        elif point == left_of_robot_points[0]:
            transit_vel = 50
            robot.MoveCart(p91, 0, 0, vel=self.config.vel_mul * transit_vel)

        robot.MoveCart(soft_point, 0, 0, vel=self.config.vel_mul * 100)
        # Transit hareketleri
        if point in right_of_robot_points and point["p_up"][0] > 400:
            transit_vel = 50
            robot.MoveCart(right_transit_point, 0, 0, vel=self.config.vel_mul * transit_vel)
        elif use_back_transit or (point["p_up"][0] > 400 and point in left_of_robot_points):
            transit_vel = 50
            robot.MoveCart(back_transit_point, 0, 0, vel=self.config.vel_mul * transit_vel)
        
        # Parça alma hareketleri
        robot.MoveCart(point["p_up"], 0, 0, vel=self.config.vel_mul * transit_vel)
        robot.MoveL(point["p"], 0, 0, vel=self.config.vel_mul * 50)
        robot.WaitMs(1000)
        robot.SetDO(7, 1)  # Parçayı kavrama sinyali
        robot.WaitMs(1000)
        robot.MoveL(point["p_up"], 0, 0, vel=self.config.vel_mul * transit_vel)
        print("PICK OBJECT", self.current_di0_value)
        if not self.current_di0_value[1]:
            print("Parça başarıyla kavrandı.")
            robot.Mode(0)
        else:
            robot.SetDO(7, 0)
            print("Parça kavurma hatası.")
            robot.Mode(1)
            current_index = self.read_current_point_index()
            self.write_current_point_index(current_index + 1)
            current_index += 1
            
            point = self.points[current_index]
            if current_index < len(left_of_robot_points + left_small + back_points):
                soft_point, self.trash = p90, p90_trash
            else:
                soft_point, self.trash = p91, p91_trash

            total_left_back_points = len(left_of_robot_points + left_small + back_points)

            use_back_transit = current_index >= len(left_of_robot_points + left_small) and current_index < total_left_back_points

            if isinstance(self.config.same_place_index, int):
                point = self.points[self.config.same_place_index]
            else:
                point = self.points[current_index]

            self.pick_point = point
            self.pick_soft_point = soft_point
            self.pick_use_back_transit = use_back_transit

            self.pick_object(point, soft_point, use_back_transit)
            

        # Geri dönüş transit hareketleri
        if point in right_of_robot_points and point["p_up"][0] > 400:
            transit_vel = 50
            robot.MoveCart(right_transit_point, 0, 0, vel=self.config.vel_mul * transit_vel)
        elif use_back_transit or (point["p_up"][0] > 400 and (point in left_of_robot_points)):
            transit_vel = 50
            robot.MoveCart(back_transit_point, 0, 0, vel=self.config.vel_mul * transit_vel)
        
        # Son hareket: Soft point'e git
        robot.MoveCart(soft_point, 0, 0, vel=self.config.vel_mul * transit_vel)

    def calculate_tolerance_distance(self, value: float, target: float, tolerance: float) -> float:
        """
        Ölçülen değer ile hedef arasındaki farkı hesaplar.
        
        Args:
            value (float): Ölçülen değer.
            target (float): Hedef değer.
            tolerance (float): Tolerans.
            
        Returns:
            float: Mutlak fark.
        """
        return np.abs(value - target)

    def get_gradient_color(self, distance: float, tolerance: float) -> str:
        """
        Mesafe farkına göre gradient renk kodu oluşturur.
        
        Args:
            distance (float): Ölçülen mesafe farkı.
            tolerance (float): Tolerans.
            
        Returns:
            str: Hex formatında renk kodu.
        """
        if distance > tolerance:
            return "FF0000"
        ratio = distance / tolerance
        red = int(255 * (1 - ratio))
        green = int(255 * (1 - ratio))
        blue = 255
        return f"{red:02X}{green:02X}{blue:02X}"

    def smol_calc(self, small_data: np.ndarray):
        """
        Small verilerini işler.
        
        Args:
            small_data (np.ndarray): Small tarama verisi.
        """
        small = self.rotate_point_cloud(small_data, -90, "z")
        small = small[small[:, 2] > np.min(small[:, 2]) + 37]
        small = small[small[:, 0] < np.min(small[:, 0]) + 50]
        small = self.to_origin(small)

        if self.config.save_point_clouds:
            self.pcd.points = o3d.utility.Vector3dVector(small)
            o3d.io.write_point_cloud("/home/eypan/Documents/down_jaguar/jaguar_measure/small.ply", self.pcd)

        circle_fitter = CircleFitter(small)
        _, z_center_small, radius_small = circle_fitter.fit_circles_and_plot(
            find_second_circle=False, val_x=0.18, val_z=0.2, delta_z=25
        )
        s_datum = circle_fitter.get_datum()
        self.dist_3mm_s, _ = circle_fitter.get_distance(second_crc=False, z_distance_to_datum=23.1)
        self.feature_3 = z_center_small - s_datum
        self.radius_small = radius_small
        self.z_center_small = z_center_small

    def hor_calc(self, horizontal_data: np.ndarray, horizontal2_data: np.ndarray):
        """
        Horizontal verilerini işler.
        
        Args:
            horizontal_data (np.ndarray): İlk horizontal tarama verisi.
            horizontal2_data (np.ndarray): İkinci horizontal tarama verisi.
        """
        horizontal2_data[:, 2] -= 70
        horizontal2_data[:, 0] -= 50

        if self.config.save_point_clouds:
            self.pcd.points = o3d.utility.Vector3dVector(horizontal2_data)
            o3d.io.write_point_cloud("/home/eypan/Documents/down_jaguar/jaguar_measure/horizontal2.ply", self.pcd)
            self.pcd.points = o3d.utility.Vector3dVector(horizontal_data)
            o3d.io.write_point_cloud("/home/eypan/Documents/down_jaguar/jaguar_measure/horizontal_pre.ply", self.pcd)

        diff = np.abs(np.max(horizontal_data[:, 0]) - np.min(horizontal2_data[:, 0]))
        datum_horizontal = np.max(horizontal_data[:, 0]) - diff

        y_values = np.linspace(np.min(horizontal_data[:, 1]), np.max(horizontal_data[:, 1]), num=100)
        line_points = np.array([[datum_horizontal, y, np.min(horizontal_data[:, 2])] for y in y_values])
        augmented_pc = np.vstack((horizontal_data, line_points))
        horizontal = self.rotate_point_cloud(augmented_pc, 90, "z")
        horizontal = self.to_origin(horizontal)
        self.horizontal = horizontal

        if self.config.save_point_clouds:
            self.pcd.points = o3d.utility.Vector3dVector(horizontal)
            o3d.io.write_point_cloud("/home/eypan/Documents/down_jaguar/jaguar_measure/horizontal_post.ply", self.pcd)

        self.circle_fitter = CircleFitter(horizontal)
        _, circle2 = self.circle_fitter.fit_circles_and_plot()
        self.dist_3mm_h = self.circle_fitter.get_distance()[0]
        self.l_40 = get_40(horizontal)
        self.height = np.max(self.horizontal[:, 1]) - self.circle_fitter.get_datum()
        self.feature_1 = circle2[1]
        self.feature_2 = circle2[2]

    def process_vertical_measurement(self, vertical_data: np.ndarray) -> dict:
        """
        Vertical verileri işleyip ölçüm sonuçlarını hesaplar.
        
        Args:
            vertical_data (np.ndarray): Vertical tarama verisi.
            
        Returns:
            dict: Hesaplama sonuçlarını içeren sözlük.
        """
        vertical = self.remove_gripper_points(vertical_data)
        vertical = self.rotate_point_cloud(vertical, 180, "z")

        if self.config.save_point_clouds:
            pcd = o3d.geometry.PointCloud()
            pcd.points = o3d.utility.Vector3dVector(vertical)
            o3d.io.write_point_cloud("/home/eypan/Documents/down_jaguar/jaguar_measure/vertical.ply", pcd)
        vertical_copy = self.to_origin(vertical.copy())
        l_17_2, ok_17_2 = horn_diff(vertical_copy)
        l_23_4, ok_23_4 = horn_diff(vertical_copy, 240, 280)

        current_index = self.get_next_valid_index(self.read_current_point_index(), self.config.ignored_points, len(self.points))
        self.write_current_point_index(current_index)
        
        if hasattr(self, "pick_point"):
            if self.config.put_back:
                point = self.pick_point
                soft_point = self.pick_soft_point
                use_back_transit = self.pick_use_back_transit
                transit_vel = 80  # Varsayılan transit hızı

                robot.MoveCart(soft_point, 0, 0, vel=self.config.vel_mul * 100)
                if point in right_of_robot_points and point["p_up"][0] > 400:
                    robot.MoveCart(right_transit_point, 0, 0, vel=self.config.vel_mul * transit_vel)
                elif use_back_transit or (point["p_up"][0] > 400 and (point in left_of_robot_points)):
                    transit_vel = 50
                    robot.MoveCart(back_transit_point, 0, 0, vel=self.config.vel_mul * transit_vel)
                
                robot.MoveCart(point["p_up"], 0, 0, vel=self.config.vel_mul * transit_vel)
                robot.MoveL(point["p"], 0, 0, vel=self.config.vel_mul * 50)
                robot.WaitMs(500)
                robot.SetDO(7, 0)  # Parçayı bırakma sinyali
                robot.WaitMs(500)
                robot.MoveL(point["p_up"], 0, 0, vel=self.config.vel_mul * transit_vel)
                
                if point in right_of_robot_points and point["p_up"][0] > 400:
                    robot.MoveCart(right_transit_point, 0, 0, vel=self.config.vel_mul * transit_vel)
                elif use_back_transit or (point["p_up"][0] > 400 and (point in left_of_robot_points)):
                    transit_vel = 50
                    robot.MoveCart(back_transit_point, 0, 0, vel=self.config.vel_mul * transit_vel)
            else:
                robot.MoveCart(self.trash, 0, 0, vel=self.config.vel_mul * 80)
                robot.SetDO(7, 0)
        elif self.config.drop_object:
            robot.MoveCart(self.trash, 0, 0, vel=self.config.vel_mul * 80)
            robot.SetDO(7, 0)

        if self.cycle == self.config.range_ - 1:
            self.write_current_point_index(0)

        B = self.circle_fitter.get_B()
        b_trans_val = np.max(vertical[:, 1]) - np.max(self.horizontal[:, 2])
        b_vertical = B + b_trans_val
        _, _, r1, l_79_73 = slope(vertical, b_vertical)
        _, _, r2, _ = slope(vertical, y_divisor=0.11, crc_l=27)
        l_42 = np.max(vertical[:, 1]) - b_vertical
        l_248 = arm_horn_lengths(vertical, b_vertical)
        mean_3mm = np.mean([self.dist_3mm_h, self.dist_3mm_s])
        l_88_6 = self.feature_1 - self.feature_2
        l_81_5 = filter_and_visualize_projection_with_ply(self.horizontal)

        return {
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

    def combine_results(self, vertical_results: dict) -> dict:
        """
        Vertical ölçüm sonuçlarını özelliklere göre birleştirir.
        
        Args:
            vertical_results (dict): Vertical ölçüm sonuçları.
            
        Returns:
            dict: Birleştirilmiş sonuçlar.
        """
        return {
            "Feature1 (102.1)": vertical_results.get("feature_1") or self.feature_1,
            "Feature2 (25mm/2)": self.feature_2,
            "Feature3 (23.1)": self.feature_3,
            "Feature4 (25mm/2)": self.radius_small,
            "Feature5 (L40)": self.l_40,
            "Feature6 (L248)": vertical_results.get("l_248"),
            "Feature7 (L42)": vertical_results.get("l_42"),
            "Feature8 (L79.73)": vertical_results.get("l_79_73"),
            "Feature9 (R1-50)": vertical_results.get("r1"),
            "Feature10 (R2-35)": vertical_results.get("r2"),
            "Feature11 (3mm)": vertical_results.get("mean_3mm"),
            "Feature12 (88.6)": vertical_results.get("l_88_6"),
            "Feature13 (10.6)": self.feature_3 - self.radius_small,
            "Feature14 (81.5)": vertical_results.get("l_81_5"),
            "Feature15 (L23.4)": vertical_results.get("l_23_4"),
            "Feature16 (L17.2)": vertical_results.get("l_17_2"),
            "Feature17 (2C)": vertical_results.get("ok_17_2")
        }

    def write_excel_to_db(self, excel_path: str):
        """
        Excel dosyasındaki verileri MariaDB'ye yazar.
        
        Args:
            excel_path (str): Excel dosya yolu.
        """
        df = pd.read_excel(excel_path, sheet_name="ScanResults")
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
        for _, row in df.iterrows():
            try:
                value_float = float(row['Value'])
            except ValueError:
                value_float = None
            data = (int(row['Iteration']), row['Feature'], value_float)
            cursor.execute(insert_query, data)
        
        conn.commit()
        cursor.close()
        conn.close()

    def save_to_excel(self):
        """
        Ölçüm sonuçlarını Excel dosyasına kaydeder.
        """
        rows = []
        for iteration, result in enumerate(self.results, start=1):
            iteration_ok = 1  # Bu iterasyon için başlangıçta OK=1 kabul ediliyor.
            for feature, value in result.items():
                rows.append({"Iteration": iteration, "Feature": feature, "Value": value})
                if feature in self.tolerances:
                    target, tolerance = self.tolerances[feature]
                    if not (target - tolerance <= value <= target + tolerance):
                        iteration_ok = 0  # Tolerans dışı kalan varsa OK=0 yap.
            rows.append({"Iteration": iteration, "Feature": "OK", "Value": iteration_ok})
        results_df = pd.DataFrame(rows)
        output_file = "/home/eypan/Documents/down_jaguar/jaguar_measure/scan_results.xlsx"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        try:
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                results_df.to_excel(writer, index=False, sheet_name="ScanResults")
                worksheet = writer.sheets["ScanResults"]
                for row_index, row in enumerate(results_df.itertuples(index=False), start=2):
                    if row.Feature == "OK":
                        row_fill = PatternFill(start_color="00B050" if row.Value else "FF0000", fill_type="solid")
                        worksheet.cell(row=row_index, column=3).fill = row_fill
                    else:        
                        iteration = row.Iteration
                        feature = row.Feature
                        value = row.Value
                        iteration_color = "FCE4D6" if iteration % 2 == 0 else "D9EAD3"
                        fill = PatternFill(start_color=iteration_color, end_color=iteration_color, fill_type="solid")
                        for col_index in range(1, len(results_df.columns) + 1):
                            worksheet.cell(row=row_index, column=col_index).fill = fill
                        if feature in self.tolerances:
                            target, tolerance = self.tolerances[feature]
                            value_cell = worksheet.cell(row=row_index, column=3)
                            if target - tolerance <= value <= target + tolerance:
                                value_cell.fill = PatternFill(start_color="00B050", fill_type="solid")
                            else:
                                value_cell.fill = PatternFill(start_color="FF0000", fill_type="solid")
                            distance = self.calculate_tolerance_distance(value, target, tolerance)
                            gradient_color = self.get_gradient_color(distance, tolerance)
                            distance_cell = worksheet.cell(row=row_index, column=4)
                            distance_cell.value = tolerance - distance
                            distance_cell.fill = PatternFill(start_color=gradient_color, fill_type="solid")
            if self.config.save_to_db:            
                self.write_excel_to_db(output_file)
        except FileNotFoundError:
            pass

    def run_scan_cycle(self):
        """
        Tarama döngüsünü çalıştırır ve tüm ölçüm işlemlerini yönetir.
        """
        ROBOT_POSITIONS = {
            'scrc': [-450, -130, 470, 82.80, 89.93, -7.30],
            'h_2': [-375, 100, 545, -90, -90, 180],
            'p_91': [-335, 100, 350, -90.00, -0.0005, 90.00],
            'notOK': [-621, 325, 511, 117, -83, -148]
        }
        MAX_RETRIES = 2  # Örnek sayı

        for self.cycle in range(self.config.range_):
            start_time = time.time()
            current_results = {}
            current_index = self.read_current_point_index()
            
            try:
                send_command({"cmd": 107, "data": {"content": "ResetAllError()"}})

                # Parça alma işlemi:
                if self.config.pick:
                    if current_index < len(left_of_robot_points + left_small + back_points):
                        soft_point, self.trash = p90, p90_trash
                    else:
                        soft_point, self.trash = p91, p91_trash

                    total_left_back_points = len(left_of_robot_points + left_small + back_points)

                    use_back_transit = current_index >= len(left_of_robot_points + left_small) and current_index < total_left_back_points

                    if isinstance(self.config.same_place_index, int):
                        point = self.points[self.config.same_place_index]
                    else:
                        point = self.points[current_index]

                    self.pick_point = point
                    self.pick_soft_point = soft_point
                    self.pick_use_back_transit = use_back_transit

                    self.pick_object(point, soft_point, use_back_transit)

                robot.MoveCart(ROBOT_POSITIONS['scrc'], 0, 0, vel=self.config.vel_mul * 100)

                # Small hesaplama:
                small_data = self.mech_eye.main(lua_name="small.lua", scan_line_count=1500)
                if self.config.use_agg:
                    thread_small = threading.Thread(target=self.smol_calc, args=(small_data,))
                    thread_small.start()
                else:
                    self.smol_calc(small_data)
                    plt.show()

                # Horizontal hesaplama:
                horizontal_data = self.mech_eye.main(lua_name="horizontal.lua", scan_line_count=1500)
                horizontal2_data = self.mech_eye.main(lua_name="horizontal2.lua", scan_line_count=1500)
                if self.config.use_agg:
                    thread_horizontal = threading.Thread(target=self.hor_calc, args=(horizontal_data, horizontal2_data))
                    thread_horizontal.start()
                else:
                    self.hor_calc(horizontal_data, horizontal2_data)
                    plt.show()

                # Vertical tarama:
                vertical_data = self.mech_eye.main(lua_name="vertical.lua", scan_line_count=2500)
                plt.show()

                if self.config.use_agg:
                    thread_small.join()
                    thread_horizontal.join()

                vertical_results = self.process_vertical_measurement(vertical_data)
                current_results = self.combine_results(vertical_results)
                current_results["Processing Time (s)"] = time.time() - start_time
            except Exception as e:
                current_results = {"Error": str(e)}
            finally:
                self.results.append(current_results)
                if self.config.use_agg:
                    t_excel = threading.Thread(target=self.save_to_excel)
                    t_excel.start()
                    self.excel_threads.append(t_excel)
                else:
                    self.save_to_excel()


if __name__ == "__main__":
    scanner = JaguarScanner(vel_mul=1)  # vel_mul => Hız çarpanı
    # Parçanın geri konulması istenmiyorsa:
    # scanner.put_back = False
    scanner.run_scan_cycle()