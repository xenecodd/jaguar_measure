from Scripts import *
from MecheyePackage import TriggerWithExternalDeviceAndFixedRate
import open3d as o3d
import numpy as np
import matplotlib
matplotlib.use('Agg')
import time

def rotate_point_cloud_y(points, angle_degrees):
    """
    Bir nokta bulutunu Y ekseni etrafında belirli bir açıyla döndür.
    :param points: Nx3 boyutunda numpy dizisi (nokta bulutu)
    :param angle_degrees: Döndürme açısı (derece cinsinden)
    :return: Döndürülmüş nokta bulutu (Nx3 numpy dizisi)
    """
    # Dereceden radyana çevir
    angle_radians = np.radians(angle_degrees)
    
    # Y ekseni etrafında dönüşüm matrisi
    rotation_matrix = np.array([
        [np.cos(angle_radians), 0, np.si5n(angle_radians)],
        [0, 1, 0],
        [-np.sin(angle_radians), 0, np.cos(angle_radians)]
    ])
    
    # Noktaları döndür
    rotated_points = points @ rotation_matrix.T
    return rotated_points

def save_point_cloud(pcd, file_path):
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


def sor_filter(numpy_points, nb_neighbors=20, std_ratio=2.0):
    """
    Numpy formatında bir nokta bulutuna SOR (Statistical Outlier Removal) filtresi uygular.

    Parameters:
        numpy_points (numpy.ndarray): Nokta bulutunu temsil eden (N, 3) boyutunda numpy dizisi.
        nb_neighbors (int): Komşuluk için değerlendirilecek nokta sayısı.
        std_ratio (float): Gürültü eşiği için standart sapma oranı.

    Returns:
        o3d.geometry.PointCloud: Gürültüden arındırılmış nokta bulutu.
    """
    # 1. Numpy dizisini Open3D nokta bulutuna çevirme
    point_cloud = o3d.geometry.PointCloud()
    point_cloud.points = o3d.utility.Vector3dVector(numpy_points)
    
    # 2. SOR filtresini uygulama
    cl, _ = point_cloud.remove_statistical_outlier(nb_neighbors=nb_neighbors, std_ratio=std_ratio)
    
    return np.asarray(cl.points)


# Initialize Mech-Eye profiler with external device and fixed rate trigger
mech_eye = TriggerWithExternalDeviceAndFixedRate()

rotated_pcd = o3d.geometry.PointCloud()

# Değerleri saklayacağımız listeler
bigcircle_centers = []
bigcircle_radii = []
kaydirak_centers_1 = []  # İlk kaydırak
kaydirak_radii_1 = []     # İlk kaydırak
kaydirak_centers_2 = []  # İkinci kaydırak
kaydirak_radii_2 = []    # İkinci kaydırak
fit_circles_centers_1 = []
fit_circles_centers_2 = []
fit_circles_radii_1 = []
fit_circles_radii_2 = []
center=[]
for i in range(1):
    
    # Horizontal nokta bulutunu almak
    horizontal = mech_eye.main(lua_name="horizontal.lua")
    rotated_pcd.points = o3d.utility.Vector3dVector(horizontal)
    o3d.io.write_point_cloud("/home/rog/Documents/scanner/transform/horizontal.ply", rotated_pcd)
    
    l_7_1 = filter_and_visualize_projection_with_ply(horizontal)
    print("l_7_1", l_7_1)
    l_40 = get_40(horizontal)
    print("l_40", l_40)
    # Fit circles hesaplama
    circle_fitter = CircleFitter(horizontal)
    start_time = time.time()
    center, _ ,ok= circle_fitter.fit_circles_and_plot()
    end_time = time.time()
    # print(f"fit_circles_and_plot süresi: {end_time - start_time:.2f} saniye")

    # Nokta bulutlarını almak
    vertical = mech_eye.main(lua_name="vertical.lua")
    rotated_pcd.points = o3d.utility.Vector3dVector(vertical)
    o3d.io.write_point_cloud("/home/rog/Documents/scanner/transform/vertical1.ply", rotated_pcd)
    
    l_17_1, ok = horn_diff(vertical)
    l_23_4, ok = horn_diff(vertical,240,280)
    print("l_17_1", l_17_1)
    print("l_23_4", l_23_4)
    
    # Nokta bulutlarının kopyalarını oluştur
    vertical_copy = vertical.copy()
    vertical_copy1 = vertical.copy()
    vertical_copy2 = vertical.copy()
    vertical_copy3 = vertical.copy()
    
    B = circle_fitter.get_B()

    b_trans_val = np.max(vertical_copy[:, 1]) - np.max(horizontal[:, 2])

    b_vertical = B + b_trans_val
    
    # Bigcircle hesaplama
    start_time = time.time()
    _, center_z, radius = bigcircle(vertical_copy1, crc=True)
    end_time = time.time()
    # print(f"bigcircle süresi: {end_time - start_time:.2f} saniye")
    bigcircle_radii.append(radius)

    _, _, radius = bigcircle(vertical_copy, "small_circle", val_x=0.90, val_y=0.2, val_z=0.05, crc=True)
    bigcircle_radii.append(radius)

    # İlk kaydırak için hesaplama
    start_time = time.time()
    _, _, r_outer, _ = kaydırak(vertical_copy2, b_vertical)
    end_time = time.time()
    # print(f"ilk kaydırak süresi: {end_time - start_time:.2f} saniye")
    kaydirak_radii_1.append(r_outer)

    z_trans_val = center[1] - center_z
    datum = circle_fitter.get_datum()

    datum_vertical = datum - z_trans_val

    # İkinci kaydırak için hesaplama
    start_time = time.time()
    _, _, r_outer, z67_1 = kaydırak(vertical_copy3, datum_vertical=datum_vertical, y_divisor=0.11, crc_l=27)
    end_time = time.time()
    # print(f"ikinci kaydırak süresi: {end_time - start_time:.2f} saniye")
    kaydirak_radii_2.append(r_outer)


    l_42 = np.max(vertical[:, 1]) - b_vertical
    print("l_42", l_42)
    arm_horn_lengths(vertical, b_vertical)
    
    

# # Ortalamadan büyük değerleri filtrele ve yazdır
# bigcircle_above_mean = [val for val in bigcircle_radii if (val < 12.50 or val > 12.76)]
# print(f"Bigcircle ortalamadan büyük yarıçap değerleri: {bigcircle_above_mean}")

# kaydirak_1_above_mean = [val for val in kaydirak_radii_1 if (val < 62.50 or val > 62.80)]
# print(f"İlk Kaydırak ortalamadan büyük yarıçap değerleri: {kaydirak_1_above_mean}")

# # Referans değer
# reference_value = 62.50

# average_distance = np.std(kaydirak_radii_1)
# print(f"62.50 std: {average_distance}")

# # Değerlerin uzaklıklarını hesapla
# distances = [abs(val - reference_value) for val in kaydirak_radii_1]
# print(f"62.50'den uzaklıklar: {distances}")

# # Uzaklıkların ortalamasını hesapla
# average_distance = np.mean(distances)
# print(f"62.50'den uzaklıkların ortalaması: {average_distance}")

# kaydirak_2_above_mean = [val for val in kaydirak_radii_2 if (val < 22.50 or val > 22.80)]
# print(f"İkinci Kaydırak ortalamadan büyük yarıçap değerleri: {kaydirak_2_above_mean}")


# average_distance = np.std(kaydirak_radii_2)
# print(f"22.50 std: {average_distance}")
