import cv2
import numpy as np
import open3d as o3d
import matplotlib.pyplot as plt
from scipy.optimize import leastsq
from MecheyePackage import edges


class CircleFitter:
    def __init__(self, pcd):
        """
        CircleFitter sınıfı, verilen nokta bulutu (pcd) üzerinde çember fitting işlemleri yapar.
        """
        self.pcd = pcd  # Nokta bulutunu numpy dizisine dönüştür
        self.commonp = None  # Şeritteki maksimum Y değeri

    def min_max_y_in_strip(self, strip_width=0.5):
        """
        X ekseninde orta noktadan geçen şeritteki Y değerinin maksimum ve minimum değerini
        sağlayan noktaların XYZ koordinatlarını bulur.
        """
        x_center = (np.min(self.pcd[:, 0]) + np.max(self.pcd[:, 0])) / 2
        strip_points = self.pcd[np.abs(self.pcd[:, 0] - x_center) < strip_width / 2]
        if len(strip_points) == 0:
            raise ValueError("Şerit içinde nokta bulunamadı.")
        
        # Y ekseninde maksimum ve minimum değerleri sağlayan noktalar
        max_idx = np.argmax(strip_points[:, 1])
        
        self.commonp = strip_points[max_idx]  # Y max noktasının XYZ koordinatları
        self.datum = np.min(strip_points[:,1])
        
        return self.commonp, self.datum

    
    def get_B(self, strip_width=20):
        points = self.pcd
        y_center = (np.min(points[:, 1]) + np.max(points[:, 1])) / 2  # Y eksenindeki orta nokta
        strip_points = points[np.abs(points[:, 1] - y_center) < strip_width / 2]  # Şeritteki noktaları seç
        if len(strip_points) == 0:
            raise ValueError("Şerit içinde nokta bulunamadı.")
        return np.max(strip_points[:, 2])
    
    def get_datum(self):
        return self.datum
    
    def get_commonp(self):
        """
        Şeritteki maksimum Y değerini döner.
        """
        if self.commonp is None:
            raise ValueError("commonp değeri henüz hesaplanmadı. max_y_in_strip çağrılmalı.")
        return self.commonp

    def fit_circle(self, x, y):
        """
        Verilen X ve Y noktalarına çember fitting yapar.
        """
        def calc_radius(xc, yc, x, y):
            return np.sqrt((x - xc)**2 + (y - yc)**2)

        def cost_function(params, x, y):
            xc, yc, r = params
            return calc_radius(xc, yc, x, y) - r

        def initial_guess(x, y):
            xc = np.mean(x)
            yc = np.mean(y)
            r = np.mean(np.sqrt((x - xc)**2 + (y - yc)**2))
            return [xc, yc, r]

        guess = initial_guess(x, y)
        result, _ = leastsq(cost_function, guess, args=(x, y))
        return result  # xc, yc, r

    def fit_circles_and_plot(self, z_1_3=102.1):
        """
        Nokta bulutunun X-Z düzleminde çember fitting işlemlerini gerçekleştirir ve görselleştirir.
        """
        try:
            self.min_max_y_in_strip()  # Şeritteki max Y değerini hesapla
            print(f"Şeritteki max Y: {self.commonp}")
            print(f"B: {self.get_B()}")
            # X-Z düzlemine projekte edilen noktalar
            projected_points_2d = self.pcd[:, [0, 1]]

            # Y ekseninde üst yarıda kalan noktaları filtrele
            y_median = np.median(projected_points_2d[:, 1])  # Y ekseni için median değer
            upper_half_points = projected_points_2d

            # Kenar koordinatlarını al (üst yarıya uygulama)
            edge_coords = edges.process_and_visualize(upper_half_points)


            # Kenarları ölçekle
            scale = edges.get_scale()
            x2d, z2d = edge_coords[:, 1] / scale, edge_coords[:, 0] / scale

            # Dinamik filtreleme parametreleri
            min_x, max_x = np.min(projected_points_2d[:, 0]), np.max(projected_points_2d[:, 0])
            min_z, max_z = np.min(projected_points_2d[:, 1]), np.max(projected_points_2d[:, 1])
            val_x, val_z = 0.2, 0.796
            x_min = min_x + val_x * (max_x - min_x)
            x_max = x_min + 28
            z_min = min_z + val_z * (max_z - min_z)
            z_max = z_min + 13

            # İlk çember fitting
            mask_1 = (x2d > x_min) & (x2d < x_max) & (z2d > z_min) & (z2d < z_max)
            x_2d_1, z_2d_1 = x2d[mask_1], z2d[mask_1]
            xc_outer, zc_outer, r_outer = self.fit_circle(x_2d_1, z_2d_1)

            # İkinci çember fitting
            zc_min_2 = zc_outer  # İlk çemberin merkezinin alt sınırı
            zc_max_2 = zc_outer + 5  # İlk çemberin üst sınırı
            mask_2 = (x2d > x_min) & (x2d < x_max) & (z2d > zc_min_2) & (z2d < zc_max_2)
            x_2d_2, z_2d_2 = x2d[mask_2], z2d[mask_2]
            xc_outer_2, zc_outer_2, r_outer_2 = self.fit_circle(x_2d_2, z_2d_2)

            # Çember çizim
            theta = np.linspace(0, 2 * np.pi, 100)

            # İlk çember çizimi
            x_outer_circle = xc_outer + r_outer * np.cos(theta)
            z_outer_circle = zc_outer + r_outer * np.sin(theta)

            # İkinci çember çizimi
            x_outer_circle_2 = xc_outer_2 + r_outer_2 * np.cos(theta)
            z_outer_circle_2 = zc_outer_2 + r_outer_2 * np.sin(theta)

            plt.figure(figsize=(8, 8))
            plt.scatter(x2d, z2d, s=1, color='blue', label='Noktalar')
            plt.plot(x_outer_circle, z_outer_circle, color='red', label=f'Çember 1 (R = {r_outer:.2f})')
            plt.plot(x_outer_circle_2, z_outer_circle_2, color='green', label=f'Çember 2 (R = {r_outer_2:.2f})')
            plt.title("X-Z Düzleminde Nokta Bulutu ve Çember Fitting")
            plt.xlabel("X")
            plt.ylabel("Z")
            plt.axis('equal')
            plt.legend()
            plt.show()

            print(f"Çember 1 Merkezi: ({xc_outer:.2f}, {zc_outer:.2f}), Yarıçap: {r_outer:.2f}")
            print(f"Çember 2 Merkezi: ({xc_outer_2:.2f}, {zc_outer_2:.2f}), Yarıçap: {r_outer_2:.2f}")
            print(f"ALT Çember merkezi tabana uzaklığı: ({zc_outer-self.datum})")
            print(f"ÜST Çember merkezi tabana uzaklığı: ({zc_outer_2-self.datum})")
            
            median =np.median(self.pcd[:,0])
            z_center = self.datum + z_1_3
            distance = np.sqrt((xc_outer - median)**2 + (zc_outer - z_center)**2)
            if (distance<3):
                ok = True
                print("merkez uzaklık_3mm",distance)
            else:
                ok = False
                print("merkez uzaklık_3mm",distance)
            return (xc_outer, zc_outer, r_outer), (xc_outer_2, zc_outer_2, r_outer_2),ok
        except Exception as e:
            print(f"Hata: {e}")



def save_3d_filter_box_as_point_cloud(file_path, x_min, x_max, y_min, y_max, z_min, z_max):
    """
    3 boyutlu filtreleme alanını bir kutu olarak nokta bulutu (PLY formatında) kaydeder.
    """
    # Çerçeve köşe noktalarını tanımla (X, Y, Z)
    box_points = np.array([
        [x_min, y_min, z_min],  # Köşe 1
        [x_max, y_min, z_min],  # Köşe 2
        [x_max, y_max, z_min],  # Köşe 3
        [x_min, y_max, z_min],  # Köşe 4
        [x_min, y_min, z_max],  # Köşe 5
        [x_max, y_min, z_max],  # Köşe 6
        [x_max, y_max, z_max],  # Köşe 7
        [x_min, y_max, z_max],  # Köşe 8
    ])

    # Kutunun kenarlarını tanımlayan noktalar (isteğe bağlı)
    edges = [
        [box_points[0], box_points[1]],  # Kenar 1
        [box_points[1], box_points[2]],  # Kenar 2
        [box_points[2], box_points[3]],  # Kenar 3
        [box_points[3], box_points[0]],  # Kenar 4
        [box_points[4], box_points[5]],  # Kenar 5
        [box_points[5], box_points[6]],  # Kenar 6
        [box_points[6], box_points[7]],  # Kenar 7
        [box_points[7], box_points[4]],  # Kenar 8
        [box_points[0], box_points[4]],  # Kenar 9
        [box_points[1], box_points[5]],  # Kenar 10
        [box_points[2], box_points[6]],  # Kenar 11
        [box_points[3], box_points[7]],  # Kenar 12
    ]

    # Kenar noktalarını nokta bulutuna dönüştür
    line_points = np.vstack(edges)

    # Open3D PointCloud oluştur ve kaydet
    box_pcd = o3d.geometry.PointCloud()
    box_pcd.points = o3d.utility.Vector3dVector(line_points)
    save_point_cloud(file_path, box_pcd)

    
    
    
def save_point_cloud(file_path,pcd):
    # Ensure that pcd is a PointCloud object, not a numpy array
    if isinstance(pcd, o3d.geometry.PointCloud):
        pcd_array = np.asarray(pcd.points)  # Convert PointCloud points to numpy array
    else:
        pcd_array = pcd  # If pcd is already a numpy array, use it directly

    # Create a new PointCloud and set the points
    pcd_new = o3d.geometry.PointCloud()
    pcd_new.points = o3d.utility.Vector3dVector(pcd_array)

    # Write the point cloud to the file
    o3d.io.write_point_cloud(file_path, pcd_new)