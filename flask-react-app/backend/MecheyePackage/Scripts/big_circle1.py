import cv2
import numpy as np
import open3d as o3d
import matplotlib.pyplot as plt
from scipy.optimize import leastsq
from scipy.stats import circstd
from Scripts import edges
import datetime
import os


class CircleFitter:
    def __init__(self, point):
        """
        CircleFitter sınıfı, verilen nokta bulutu (pcd) üzerinde çember fitting işlemleri yapar.
        """
        self.pcd = point
        self.commonp = None
        self.datum = self.get_datum()

    def get_B(self, strip_width=20):
        points = self.pcd
        medianx = np.median(points[:, 0])
        mediany = np.median(points[:, 1])  # Y eksenindeki orta nokta
        strip_points = points[(np.abs(points[:, 1] - mediany) < strip_width / 2) & 
                              (np.abs(points[:, 0] - medianx) < strip_width / 2)]
        if len(strip_points) == 0:
            raise ValueError("Şerit içinde nokta bulunamadı.")
        return np.max(strip_points[:, 2])
    
    def get_datum(self):
        strip_width = 1
        x_center = np.median(self.pcd[:, 0])
        strip_points = self.pcd[np.abs(self.pcd[:, 0] - x_center) < strip_width / 2]
        self.datum = np.min(strip_points[:, 1])
        return self.datum

    def calculate_error_metrics(self, x_points, y_points, xc, yc, r, circle_name="Circle"):
        """
        Çember fitting için hata metriklerini hesaplar ve txt dosyasına yazar.
        
        Args:
            x_points, y_points: Çember fitting yapılan noktalar
            xc, yc, r: Hesaplanan çember merkezi ve yarıçapı
            circle_name: Çember ismi (Circle 1, Circle 2 vb.)
        """
        n_points = len(x_points)

        # Her nokta için çember merkezine olan mesafe
        distances_to_center = np.sqrt((x_points - xc)**2 + (y_points - yc)**2)

        # Geometrik hata: Her noktanın çember üzerinden sapması
        geometric_errors = np.abs(distances_to_center - r)

        # Hata metrikleri
        mean_error = np.mean(geometric_errors)
        rms_error = np.sqrt(np.mean(geometric_errors**2))
        std_deviation = np.std(geometric_errors)
        max_error = np.max(geometric_errors)
        min_error = np.min(geometric_errors)

        # Açısal analiz
        angles_rad = np.arctan2(y_points - yc, x_points - xc)
        angles_deg = np.degrees(angles_rad)
        angles_deg[angles_deg < 0] += 360  # 0-360 normalize et

        # Açısal dağılım metrikleri
        angle_range = np.max(angles_deg) - np.min(angles_deg)
        angle_mean = np.mean(angles_deg)

        # ✅ Circular (dairesel) standart sapma – doğru yöntem
        angle_std = np.degrees(circstd(angles_rad, high=2*np.pi, low=0))

        # Açısal sektörlerde dağılım (her 45° bir sektör)
        sectors = np.floor(angles_deg / 45).astype(int)
        sector_counts = np.bincount(sectors, minlength=8)

        # TXT dosyasına yaz
        timestamp = datetime.datetime.now().strftime("%d_%H%M")
        filename = f"{circle_name}{timestamp}.txt"
        mode = 'a' if os.path.exists(filename) else 'w'

        with open(filename, mode, encoding='utf-8') as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"ÇEMBER FİTTİNG ANALİZİ - {circle_name}\n")
            f.write(f"Analiz Zamanı: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*60}\n\n")

            f.write(f"GENEL BİLGİLER:\n")
            f.write(f"Nokta Sayısı: {n_points}\n")
            f.write(f"Çember Merkezi: ({xc:.4f}, {yc:.4f})\n")
            f.write(f"Yarıçap: {r:.4f}\n\n")

            f.write(f"GEOMETRİK HATA METRİKLERİ:\n")
            f.write(f"Ortalama Hata: {mean_error:.6f}\n")
            f.write(f"RMS Hata: {rms_error:.6f}\n")
            f.write(f"Standart Sapma: {std_deviation:.6f}\n")
            f.write(f"Maksimum Hata: {max_error:.6f}\n")
            f.write(f"Minimum Hata: {min_error:.6f}\n\n")

            f.write(f"AÇISAL DAĞILIM ANALİZİ:\n")
            f.write(f"Açı Aralığı: {angle_range:.2f}°\n")
            f.write(f"Açısal Ortalama: {angle_mean:.2f}°\n")
            f.write(f"Açısal Standart Sapma (circular): {angle_std:.2f}°\n\n")

            f.write(f"SEKTÖR DAĞILIMI (45° sektörler):\n")
            for i, count in enumerate(sector_counts):
                start_angle = i * 45
                end_angle = (i + 1) * 45
                f.write(f"Sektör {i+1} ({start_angle}°-{end_angle}°): {count} nokta\n")

            f.write(f"\n{'='*60}\n")

        print(f"Hata metrikleri {filename} dosyasına kaydedildi.")

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

    def fit_circles_and_plot(self, name, find_second_circle=True, val_x=0.18, val_z=0.796, delta_z=14, clc_metrics=False):

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
            
            # X-Z düzlemine projekte edilen noktalar
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
            x_max = x_min + 26
            z_min = min_z + val_z * (max_z - min_z)
            z_max = z_min + delta_z

            # İlk çember fitting
            mask_1 = (x2d > x_min) & (x2d < x_max) & (z2d > z_min) & (z2d < z_max)
            x_2d_1, z_2d_1 = x2d[mask_1], z2d[mask_1]
            xc_outer, zc_outer, r_outer = self.fit_circle(x_2d_1, z_2d_1)
            self.xc_outer, self.zc_outer = xc_outer, zc_outer

            # İlk çember için hata metriklerini hesapla
            if clc_metrics:
                self.calculate_error_metrics(x_2d_1, z_2d_1, xc_outer, zc_outer, r_outer, name)

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

            if find_second_circle:
                return (xc_outer, zc_outer, r_outer), (xc_outer_2, zc_outer_2, r_outer_2)
            else:
                return (xc_outer, zc_outer, r_outer)

        except Exception as e:
            print(f"Hata: {e}")