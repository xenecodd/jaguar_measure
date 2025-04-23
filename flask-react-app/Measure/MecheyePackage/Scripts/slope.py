import numpy as np
import open3d as o3d
import matplotlib.pyplot as plt
from scipy.optimize import leastsq
from Scripts import edges
import os

def read_current_point_index() -> int:
    if os.path.exists(config["file_path"]):
        with open(config["file_path"], 'r') as file:
            return int(file.read().strip())
    return 0

# Çember fitting için yardımcı fonksiyonlar
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

def slope(pcd, b_vertical=None, y_divisor=0.21, delta_y=0.5, crc_l=57.67):
    """
    Nokta bulutu üzerinde kaydırma, filtreleme ve çember fitting işlemleri yapar.

    Parameters:
    - points: numpy.ndarray, giriş nokta bulutu (Nx3 boyutunda).
    - y_divisor: float, Y ekseninde filtreleme için bölme faktörü.
    - delta_y: float, X ekseni için filtreleme genişliği.
    - crc_l: float, Y ekseninde filtreleme uzunluğu.

    Returns:
    - yc, zc: float, fitted circle'ın merkezi koordinatları.
    - r_outer: float, fitted circle'ın yarıçapı.
    """
    
    points = np.asarray(pcd).copy()
    l79_73 = 0
    
    # Y eksenini ters çevir
    points[:, 1] = -points[:, 1]
    
    # Minimum değerleri çıkararak noktaları kaydır
    min_vals = np.min(points, axis=0)
    points -= min_vals
            

    # Min ve max değerleri hesapla
    x_min, x_max = np.min(points[:, 0]), np.max(points[:, 0])
    y_min, y_max = np.min(points[:, 1]), np.max(points[:, 1])
    z_min, z_max = np.min(points[:, 2]), np.max(points[:, 2])

    # Y ve Z ekseni filtreleme sınırlarını belirle
    y_min_filter = y_min + (y_divisor * (y_max - y_min)) - 2
    y_max_filter = y_min_filter + crc_l
    x_center = (x_min + x_max) / 2

    z_min_filter = z_min + 0.05 * (z_max - z_min)
    z_max_filter = z_min_filter + 100

    # Filtreleme işlemi
    filtered_points = points[
        (points[:, 0] > x_center - delta_y) &
        (points[:, 0] < x_center + delta_y) &
        (points[:, 1] > y_min_filter) &
        (points[:, 1] < y_max_filter)
    ]

    # Kenar işleme (2D)
    projected_points_2d = edges.process_and_visualize(filtered_points[:, [1, 2]])
    # projected_points_2d = filtered_points[:, [1, 2]]
    # Çember fitting için 2D koordinatlar
    scale= edges.get_scale()
    y_2d, z_2d = projected_points_2d[:, 1] / scale, projected_points_2d[:, 0] / scale
    
    # Başlangıç tahmini ve fitting işlemi
    guess = initial_guess(y_2d, z_2d)
    result, _ = leastsq(cost_function, guess, args=(y_2d, z_2d))
    yc, zc, r_outer = result

    # print(f"Seçilen çemberin merkezi: ({yc:.2f}, {zc:.2f}), Yarıçap: {r_outer:.2f}")

    if b_vertical:
        b_vertical= - b_vertical
        b_vertical= b_vertical - min_vals[1]
        l79_73 =  yc - b_vertical
        # print("l_79_73",l79_73)
    
    # Çember noktalarını oluştur
    theta = np.linspace(0, 2 * np.pi, 100)
    circle_y = yc + r_outer * np.cos(theta)
    circle_z = zc + r_outer * np.sin(theta)
    print("Slope is here")
    # Görselleştirme
    plt.figure(figsize=(8, 8))
    plt.scatter(points[:,1], points[:,2], color='green', label='Noktalar')
    plt.scatter(y_2d, z_2d, color='blue', label='Noktalar')
    plt.plot(circle_y, circle_z, color='red', label=f'Fitted Circle (r={r_outer:.2f})')
    plt.title("Y-Z Düzleminde Nokta Bulutu ve Çember Fitting")
    plt.xlabel("Y")
    plt.ylabel("Z")
    plt.axis('equal')
    plt.legend()
    plt.grid(True)

    # Open3D ile 3D görselleştirme
    filtered_pcd = o3d.geometry.PointCloud()
    filtered_pcd.points = o3d.utility.Vector3dVector(filtered_points)
    filtered_pcd.paint_uniform_color([0, 0, 1])  # Mavi renk
    filtered_pcd2 = o3d.geometry.PointCloud()
    filtered_pcd2.points = o3d.utility.Vector3dVector(points)
    filtered_pcd2.paint_uniform_color([1, 0, 0])  # Kırmızı renk

    # # Filtrelenmiş noktaları kaydetme
    # index = read_current_point_index()
    # if b_vertical:
    #     slope_name = f"r1_50_{index}"
    #     o3d.io.write_point_cloud(f"/home/eypan/Projects/JaguarWorks/jaguar_measure/flask-react-app/Measure/MecheyePackage/Slope_outputs/all_points_{index}.ply", filtered_pcd2)
    # else:
    #     slope_name = f"r2_35_{index}"
    # o3d.io.write_point_cloud(f"/home/eypan/Projects/JaguarWorks/jaguar_measure/flask-react-app/Measure/MecheyePackage/Slope_outputs/{slope_name}.ply", filtered_pcd)
    
    return yc, zc, r_outer, l79_73
