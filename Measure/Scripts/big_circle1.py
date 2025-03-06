import cv2
import numpy as np
import open3d as o3d
import matplotlib.pyplot as plt
from scipy.optimize import leastsq
from Measure.Scripts import edges



class CircleFitter:
    def __init__(self, point):
        """
        CircleFitter sınıfı, verilen nokta bulutu (pcd) üzerinde çember fitting işlemleri yapar.
        """

        self.pcd = point
        self.commonp = None
        self.datum = self.get_datum()  # Initialize datum


    # def max_y_strip(self):
    #     """
    #     Şerit içindeki noktaların minimum ve maksimum Y koordinatlarını döndürür.
    #     """
    #     points = self.pcd
    #     x_center = (np.min(points[:, 0]) + np.max(points[:, 0])) / 2  # Y eksenindeki orta nokta
    #     strip_points = points[np.abs(points[:, 0] - x_center) < 5]  # Şeritteki noktaları seç
    #     if len(strip_points) == 0:  
    #         raise ValueError("Şerit içinde nokta bulunamadı.")
    #     return (np.max(strip_points[:, 1])+self.min_old)

    def get_B(self, strip_width=20):
        points = self.pcd
        medianx =np.median(points[:, 0])
        mediany = np.median(points[:, 1]) # Y eksenindeki orta nokta
        strip_points = points[(np.abs(points[:, 1] - mediany) < strip_width / 2) & 
                              (np.abs(points[:, 0] - medianx) < strip_width / 2)]
        if len(strip_points) == 0:
            raise ValueError("Şerit içinde nokta bulunamadı.")
        return np.min(strip_points[:, 2])
    
    def get_datum(self):
        strip_width = 1
        x_center = np.median(self.pcd[:, 0])
        strip_points = self.pcd[np.abs(self.pcd[:, 0] - x_center) < strip_width / 2]
        self.datum = np.min(strip_points[:,1])
        return self.datum
    
    def get_distance(self, second_crc=True, z_distance_to_datum=102.1, reel_datum=None):
        """
        Çember merkezinin doğru noktaya öklid mesafesini hesaplar ve görselleştirir.
        Orijinal pcd üzerindeki noktalar ve hesaplanan merkezleri çizer.

        Args:
            second_crc (bool): İkinci çemberin merkezini kullanıp kullanmayacağınızı belirtir.
            z_distance_to_datum (float): Datum'a göre z mesafesi.
            reel_datum (float, optional): Gerçek datum değeri. Varsayılan olarak self.datum kullanılır.

        Returns:
            distance (float): Çember merkezinin uzaklığı.
            ok (bool): Mesafenin 3 mm'den küçük olup olmadığını kontrol eder.
        """
        datum = self.datum

        # Çember merkezlerini seç
        if second_crc:
            median = np.median(self.pcd[:, 0])
            xc_outer, zc_outer = self.xc_outer_2, self.zc_outer_2
        else:
            median = np.median(self.pcd[:, 0])
            xc_outer, zc_outer = self.xc_outer, self.zc_outer

        # Median ve z_center hesaplamaları
        
        z_center = datum + z_distance_to_datum

        # Öklid mesafesi
        distance = np.hypot(xc_outer - median, zc_outer - z_center)

        # Mesafenin doğruluk kontrolü
        ok = distance < 3

        # Bilgileri yazdır
        print(f"Çember Merkezi: ({xc_outer:.2f}, {zc_outer:.2f})")
        print(f"z_center: {z_center:.2f}, Median: {median:.2f}")
        print(f"Mesafe: {distance:.2f} mm, Durum: {'OK' if ok else 'HATA'}")

        # Görselleştirme
        plt.figure(figsize=(8, 8))
        plt.scatter(self.pcd[:, 0], self.pcd[:, 1], s=1, color='blue', label='Orijinal Noktalar')
        plt.scatter(median, z_center, color='orange', label='z_center (Referans Nokta)')
        plt.scatter(xc_outer, zc_outer, color='red', label='Çember Merkezi')
        plt.title("Çember Merkezi ve Referans Nokta")
        plt.xlabel("X")
        plt.ylabel("Z")
        plt.axis('equal')
        plt.legend()

        return distance, ok

    

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

    def fit_circles_and_plot(self, find_second_circle=True, val_x=0.18, val_z=0.796, delta_z=13):
        """
        Nokta bulutunun X-Z düzleminde çember fitting işlemlerini gerçekleştirir ve görselleştirir.
        
        Args:
            find_second_circle (bool): İkinci çemberi bulup bulmama seçeneği.
            val_x (float): Dinamik filtreleme için X eksenindeki oran.
            val_z (float): Dinamik filtreleme için Z eksenindeki oran.
            delta_z (float): Filtreleme bölgesinin Z eksenindeki genişliği.
        """
        try:
            self.find_second_circle = find_second_circle
            print(f"B: {self.get_B()}")
            
            # X-Z düzlemine projekte edilen noktalar
            rotated_pcd = o3d.geometry.PointCloud()
            # rotated_pcd.points = o3d.utility.Vector3dVector(self.pcd)
            # o3d.io.write_point_cloud("/home/eypan/Documents/scanner/jaguar_measure/bigcrc.ply", rotated_pcd)
            projected_points_2d = self.pcd[:, [0, 1]]

            # Kenar koordinatlarını al
            edge_coords = edges.process_and_visualize(projected_points_2d)

            # Kenarları ölçekle
            scale = edges.get_scale()
            x2d, z2d = edge_coords[:, 1] / scale, edge_coords[:, 0] / scale

            # Dinamik filtreleme parametreleri
            min_x, max_x = np.min(projected_points_2d[:, 0]), np.max(projected_points_2d[:, 0])
            min_z, max_z = np.min(projected_points_2d[:, 1]), np.max(projected_points_2d[:, 1])
            x_min = min_x + val_x * (max_x - min_x)
            x_max = x_min + 28
            z_min = min_z + val_z * (max_z - min_z)
            z_max = z_min + delta_z

            # İlk çember fitting
            mask_1 = (x2d > x_min) & (x2d < x_max) & (z2d > z_min) & (z2d < z_max)
            x_2d_1, z_2d_1 = x2d[mask_1], z2d[mask_1]
            xc_outer, zc_outer, r_outer = self.fit_circle(x_2d_1, z_2d_1)
            self.xc_outer, self.zc_outer = xc_outer, zc_outer

            # Çemberlerin çizimi
            theta = np.linspace(0, 2 * np.pi, 100)
            x_outer_circle = xc_outer + r_outer * np.cos(theta)
            z_outer_circle = zc_outer + r_outer * np.sin(theta)

            # Görselleştirme
            plt.figure(figsize=(8, 8))
            plt.scatter(x2d, z2d, s=1, color='blue', label='Noktalar')
            plt.plot(x_outer_circle, z_outer_circle, color='red', label=f'Çember 1 (R = {r_outer:.2f})')

            # Filtreleme alanını kare şeklinde çiz
            plt.gca().add_patch(
                plt.Rectangle(
                    (x_min, z_min),  # Dikdörtgenin sol alt köşesi
                    x_max - x_min,   # Genişlik
                    z_max - z_min,   # Yükseklik
                    edgecolor='red', facecolor='none', linewidth=2, label='Filtreleme Bölgesi'
                )
            )

            if find_second_circle:
                # İkinci çember fitting
                zc_min_2 = zc_outer  # İlk çemberin merkezinin alt sınırı
                zc_max_2 = zc_outer + 5  # İlk çemberin üst sınırı
                mask_2 = (x2d > x_min) & (x2d < x_max) & (z2d > zc_min_2) & (z2d < zc_max_2)
                x_2d_2, z_2d_2 = x2d[mask_2], z2d[mask_2]
                xc_outer_2, zc_outer_2, r_outer_2 = self.fit_circle(x_2d_2, z_2d_2)
                self.xc_outer_2, self.zc_outer_2 = xc_outer_2, zc_outer_2

                # İkinci çember çizimi
                x_outer_circle_2 = xc_outer_2 + r_outer_2 * np.cos(theta)
                z_outer_circle_2 = zc_outer_2 + r_outer_2 * np.sin(theta)
                plt.plot(x_outer_circle_2, z_outer_circle_2, color='green', label=f'Çember 2 (R = {r_outer_2:.2f})')

            plt.title("X-Z Düzleminde Nokta Bulutu, Çember Fitting ve Filtreleme Alanı")
            plt.xlabel("X")
            plt.ylabel("Z")
            plt.axis('equal')
            plt.legend()

            print(f"Çember 1 Merkezi: ({xc_outer:.2f}, {zc_outer:.2f}), Yarıçap: {r_outer:.2f}")
            if find_second_circle:
                print(f"Çember 2 Merkezi: ({xc_outer_2:.2f}, {zc_outer_2:.2f}), Yarıçap: {r_outer_2:.2f}")
                return (xc_outer, zc_outer, r_outer), (xc_outer_2, zc_outer_2, r_outer_2)
            else:
                return (xc_outer, zc_outer, r_outer)

        except Exception as e:
            print(f"Hata: {e}")