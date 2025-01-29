import open3d as o3d
import numpy as np
import matplotlib.pyplot as plt
def get_40(points):
    x_min = np.min(points[:, 0])  # X eksenindeki minimum değer
    x_max = np.max(points[:, 0])  # X eksenindeki maksimum değer
    x_width = x_max - x_min  # Genişlik (fark)
    return x_width



def horn_diff(pcd, y_offset_low=60, y_offset_high=100, z_threshold=8):
    """
    Nokta bulutunun X-Y düzlemindeki sol ve sağ bölgesini analiz eder ve farkları görselleştirir.

    Parameters:
    - points: numpy.ndarray, 3D noktaları içeren bir dizi (Nx3).
    - y_offset_low: float, Y ekseninde alt limit için offset.
    - y_offset_high: float, Y ekseninde üst limit için offset.
    - z_threshold: float, Z eksenindeki üst noktalardan seçme eşiği.

    Returns:
    - x_difference: float, sol ve sağ bölge arasındaki X farkı.
    """
    points = np.asarray(pcd).copy()
    # Medyan ve Y-Z eksenindeki filtreleme aralıkları
    median = np.median(points[:, 0])
    y_min, y_max = np.min(points[:, 1]) + y_offset_low, np.min(points[:, 1]) + y_offset_high

    # Sol ve sağ bölgeleri filtrele
    left = points[
        (points[:, 0] < median) & (points[:, 1] > y_min) & (points[:, 1] < y_max)
    ]
    right = points[
        (points[:, 0] > median) & (points[:, 1] > y_min) & (points[:, 1] < y_max)
    ]

    # Sol ve sağ bölgeleri Z eksenine göre filtrele
    left = left[left[:, 2] > np.max(left[:, 2]) - z_threshold] if len(left) > 0 else []
    right = right[right[:, 2] > np.max(right[:, 2]) - z_threshold] if len(right) > 0 else []
    
    
    left_max = np.max(left[:, 0]) if len(left) > 0 else None
    right_min = np.min(right[:, 0]) if len(right) > 0 else None

    if left_max is not None and right_min is not None:
        center = (left_max + right_min) / 2
        difference = np.abs(median - center)
        
        if difference > 1:
            ok = False
            print("feature14", difference)
        else:
            ok = True
            print("feature14", difference)
    
    
    # # Görselleştirme
    # plt.figure(figsize=(8, 8))
    # plt.scatter(points[:, 0], points[:, 1], s=1, color='blue', alpha=0.5, label='Object')
    # plt.scatter(left[:, 0], left[:, 1], s=10, color='green', label='Left')
    # plt.scatter(right[:, 0], right[:, 1], s=10, color='red', label='Right')
    # plt.title("X-Y Düzleminde Boynuz Farkları")
    # plt.xlabel("X")
    # plt.ylabel("Y")
    # plt.axis('equal')
    # plt.legend()
    # plt.grid(True)
    # plt.show()

    # X farkını hesapla
    if len(left) > 0 and len(right) > 0:
        return np.min(right[:, 0]) - np.max(left[:, 0]),difference
    else:
        print("Sol veya sağ bölge için yeterli nokta yok.")
        return 0



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
    print("l_81_5:", l_81_5)
    # l_88_6 = 0
    # l_81_5 = 0
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
    plt.show()

    return l_81_5

