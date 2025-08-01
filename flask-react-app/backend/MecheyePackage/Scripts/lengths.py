import open3d as o3d
import numpy as np
import matplotlib.pyplot as plt
from Scripts import edges
import logging 
from numpy import isfinite

logger = logging.getLogger(__name__)

def get_40(points, debug=False):
    """
    Gelişmiş hassasiyet kontrolü ile nokta bulutu verilerinin genişliğini (x-ekseni aralığı) hesaplar.
    
    Args:
        points (np.ndarray): (N, 3) şeklinde nokta bulutu verisi
        debug (bool): Hata ayıklama çıktısını etkinleştir
    
    Returns:
        float: 5 ondalık basamağa yuvarlanmış genişlik
    """
    if points.size == 0:
        logger.warning("get_40 fonksiyonuna boş nokta bulutu verildi")
        return 0.0
    
    if points.shape[1] < 1:
        logger.error("Nokta bulutu en az x-koordinatlarına sahip olmalıdır (shape[1] >= 1)")
        return 0.0
    
    # X-koordinatlarını çıkar
    x_coords = points[:, 0]
    
    # Potansiyel NaN veya sonsuz değerleri kaldır
    valid_x = x_coords[isfinite(x_coords)]
    
    if len(valid_x) == 0:
        logger.warning("Nokta bulutunda geçerli x-koordinatı bulunamadı")
        return 0.0
    
    # Daha yüksek hassasiyetle min ve max hesapla
    # Yalnızca y ekseni ymax ile ymax - 50 arasındaki noktaları seç
    y_max = np.max(points[:, 1])
    y_min_range = y_max - 50
    mask = (points[:, 1] <= y_max) & (points[:, 1] >= y_min_range)
    x_coords_in_y_range = points[mask, 0]
    valid_x = x_coords_in_y_range[isfinite(x_coords_in_y_range)]

    x_min = np.min(valid_x)
    x_max = np.max(valid_x)
    
    # Genişliği hesapla
    x_width_raw = x_max - x_min
    
    # Kayan nokta hassasiyet sorunlarından kaçınmak için 5 ondalık basamağa yuvarla
    x_width = round(x_width_raw, 5)
    
    if debug:
        logger.info(f"get_40 Hata Ayıklama Bilgisi:")
        logger.info(f"  Nokta bulutu şekli: {points.shape}")
        logger.info(f"  Geçerli x-koordinatları: {len(valid_x)}")
        logger.info(f"  X min: {x_min:.10f}")
        logger.info(f"  X max: {x_max:.10f}")
        logger.info(f"  Ham genişlik: {x_width_raw:.15f}")
        logger.info(f"  Yuvarlanmış genişlik: {x_width}")
        logger.info(f"  X aralığı: [{np.min(valid_x):.6f}, {np.max(valid_x):.6f}]")
        logger.info(f"  X'in standart sapması: {np.std(valid_x):.6f}")
    
    return x_width

def save_filtered_point_cloud(points_array, file_path):
    if points_array.size > 0:
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points_array)
        o3d.io.write_point_cloud(file_path, pcd)
    else:
        print(f"'{file_path}' boş bir veri içeriyor, kaydedilmedi.")

def arm_horn_lengths(points, b_vertical=None):
    if b_vertical is None:
        raise ValueError("b_vertical değeri None olamaz.")

    # Y ve Z eksenlerinde min-max
    min_y, max_y = np.min(points[:, 1]), np.max(points[:, 1])
    min_z, max_z = np.min(points[:, 2]), np.max(points[:, 2])

    # Filtreleme parametreleri
    val_y = 0.1
    val_z = 0.25

    y_min = min_y + val_y * (max_y - min_y)
    y_max = y_min + 80
    z_min = min_z + val_z * (max_z - min_z)
    z_max = z_min + 50

    y_min2, y_max2 = y_min + 70, y_max + 90
    z_min2, z_max2 = z_min + 62, z_max + 75

    # X merkezine göre bölme
    x_center = (np.max(points[:, 0]) + np.min(points[:, 0])) / 2
    delta_x = 1

    # Filtrelenmiş noktalar
    filtered_points = points[
        (points[:, 1] > y_min) & (points[:, 1] < y_max) &
        (points[:, 2] > z_min) & (points[:, 2] < z_max)
    ]

    filtered_points2 = points[
        (points[:, 1] > y_min2) & (points[:, 1] < y_max2) &
        (points[:, 2] > z_min) & (points[:, 2] < z_max)
    ]

    filtered_points3 = points[
        (points[:, 2] > z_min2) & (points[:, 2] < z_max2)
    ]

    # Boş veri kontrolü
    if filtered_points.size == 0 or filtered_points2.size == 0 or filtered_points3.size == 0:
        print("Uyarı: Filtrelenmiş nokta bulutlarından biri boş!")

    # save_filtered_point_cloud(filtered_points, "filtered_points.ply")
    # save_filtered_point_cloud(filtered_points2, "filtered_points2.ply")
    # save_filtered_point_cloud(filtered_points3, "filtered_points3.ply")

    l_248 = b_vertical - np.min(points[:, 1])
    return l_248

def horn_diff(points, y_offset_low=60, y_offset_high=100, z_threshold=8, margin_fraction=0.05):
    """
    Nokta bulutunun X-Y düzlemindeki sol ve sağ bölgesini analiz eder, 
    kenar noktalarını belirler ve kenar çizgisine yakın noktaların ortalamasıyla 
    yeni left ve right değerlerini hesaplayıp farklarını görselleştirir.

    Parameters:
    - points: numpy.ndarray, 3D noktaları içeren dizi (Nx3).
    - y_offset_low: float, Y ekseninde alt limit için offset.
    - y_offset_high: float, Y ekseninde üst limit için offset.
    - z_threshold: float, Z eksenindeki üst noktalardan seçme eşiği.
    - margin_fraction: float, kenar nokta seçiminde, grubun x aralığının kullanılacak oranı.

    Returns:
    - x_difference: float, yeni left ve right arasındaki fark.
    - difference: float, medyan ile hesaplanan merkez arasındaki fark.
    """
    import numpy as np
    import matplotlib.pyplot as plt

    # Medyan x değeri
    median = np.median(points[:, 0])
    y_min = np.min(points[:, 1]) + y_offset_low
    y_max_val = np.min(points[:, 1]) + y_offset_high

    # Sol ve sağ bölgeleri filtrele
    left = points[(points[:, 0] < median) & (points[:, 1] > y_min) & (points[:, 1] < y_max_val)]
    right = points[(points[:, 0] > median) & (points[:, 1] > y_min) & (points[:, 1] < y_max_val)]

    # Z ekseni filtresi: Yeterli veri varsa
    left = left[left[:, 2] > (np.max(left[:, 2]) - z_threshold)] if left.size > 0 else np.empty((0, 3))
    right = right[right[:, 2] > (np.max(right[:, 2]) - z_threshold)] if right.size > 0 else np.empty((0, 3))

    # Kenar işlemleri: edges modülündeki fonksiyonu çağır (varsayım: edges modülü mevcut)
    if left.size > 0:
        processed_left = edges.process_and_visualize(left[:, [0, 1]])
        if isinstance(processed_left, tuple):
            processed_left = processed_left[0]
        processed_left = np.array(processed_left)
    else:
        processed_left = np.empty((0, 2))

    if right.size > 0:
        processed_right = edges.process_and_visualize(right[:, [0, 1]])
        if isinstance(processed_right, tuple):
            processed_right = processed_right[0]
        processed_right = np.array(processed_right)
    else:
        processed_right = np.empty((0, 2))

    # Ölçek bilgisini al
    scale = edges.get_scale()

    # İşlenmiş verileri iki boyutlu diziye dönüştür.
    # Not: sütun sırası; ilk sütun x değeri, ikinci sütun y değeri.
    if processed_left.size > 0:
        left_arr = np.column_stack((processed_left[:, 1] / scale, processed_left[:, 0] / scale))
    else:
        left_arr = np.empty((0, 2))
    if processed_right.size > 0:
        right_arr = np.column_stack((processed_right[:, 1] / scale, processed_right[:, 0] / scale))
    else:
        right_arr = np.empty((0, 2))

    # left_arr'deki en yüksek x değerine yakın (kenar) noktaların ortalaması
    if left_arr.size > 0:
        max_left_val = np.max(left_arr[:, 0])
        left_range = max_left_val - np.min(left_arr[:, 0])
        left_margin = left_range * margin_fraction
        left_edge_points = left_arr[left_arr[:, 0] >= max_left_val - left_margin]
        new_left = np.mean(left_edge_points[:, 0])
    else:
        new_left = None

    # right_arr'deki en düşük x değerine yakın (kenar) noktaların ortalaması
    if right_arr.size > 0:
        min_right_val = np.min(right_arr[:, 0])
        right_range = np.max(right_arr[:, 0]) - min_right_val
        right_margin = right_range * margin_fraction
        right_edge_points = right_arr[right_arr[:, 0] <= min_right_val + right_margin]
        new_right = np.mean(right_edge_points[:, 0])
    else:
        new_right = None

    # Hesaplamalar ve görselleştirme
    if new_left is not None and new_right is not None:
        center = (new_left + new_right) / 2
        difference = np.abs(median - center)
        # print("feature14", difference)
        x_difference = new_right - new_left

        plt.figure(figsize=(8, 8))
        plt.scatter(points[:, 0], points[:, 1], s=1, color='blue', alpha=0.5, label='Object')
        plt.scatter(left_arr[:, 0], left_arr[:, 1], s=10, color='green', label='Left')
        plt.scatter(right_arr[:, 0], right_arr[:, 1], s=10, color='red', label='Right')
        # Yeni kenar ortalamalarını gösteren çizgiler
        plt.axvline(new_left, color='green', linestyle='--', label='New Left')
        plt.axvline(new_right, color='red', linestyle='--', label='New Right')
        plt.title("X-Y Düzleminde Boynuz Farkları")
        plt.xlabel("X")
        plt.ylabel("Y")
        plt.axis('equal')
        plt.legend()
        plt.grid(True)
        plt.show()

        return x_difference, difference
    else:
        # print("Sol veya sağ bölge için yeterli nokta yok.")
        return 0, 0

def filter_and_visualize_projection_with_ply(points):
    # X ekseninde ortadaki bölgeyi seç
    median = np.median(points[:, 0])

    # Y ekseninde max Y değeri ve max Y - 40 arası, Z ekseninde max Z - 15 arası filtreleme
    y_max = np.max(points[:, 1])
    z_max = np.max(points[:, 2])

    # Filtreleme işlemi
    projected_points_2d = points[
        (points[:, 0] < median + 1) &
        (points[:, 0] > median - 1) &
        (points[:, 1] < y_max) &
        (points[:, 1] > y_max - 50) &
        (points[:, 2] > z_max - 13)
    ]
    
    l_81_5 = np.min(projected_points_2d[:, 1])-np.min(points[:, 1])
    l_7_1 = np.max(projected_points_2d[:, 1])-np.min(projected_points_2d[:, 1])
    # Görselleştirme
    plt.figure(figsize=(8, 8))
    plt.scatter(points[:, 2], points[:, 1], color='red', s=1, label="All Points (Y-Z Proj.)")
    plt.scatter(projected_points_2d[:, 2], projected_points_2d[:, 1], color='blue', s=1, label="Filtered Region (Y-Z Proj.)")
    plt.title("Y-Z Düzleminde Filtrelenmiş Bölge ve Tüm Noktalar")
    plt.xlabel("Y")
    plt.ylabel("Z")
    plt.axis('equal')
    plt.legend()
    plt.grid(True)  

    return l_81_5, l_7_1
