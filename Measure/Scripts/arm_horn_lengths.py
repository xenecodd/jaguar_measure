
import numpy as np
import open3d as o3d

def arm_horn_lengths(points, b_vertical=None):

    # Yeni minimum ve maksimum değerleri yazdır
    min_y, max_y = np.min(points[:, 1]), np.max(points[:, 1])
    min_z, max_z = np.min(points[:, 2]), np.max(points[:, 2])
    # print(min_x, min_y, min_z)

    val_y = 0.1
    val_z = 0.25
    # Hesaplamalar: Bölme değerlerini kullanarak filtreleme parametrelerini dinamik hale getirme

    y_min = min_y + val_y * (max_y - min_y)
    y_max = y_min + 80
    z_min = min_z + val_z * (max_z - min_z)
    z_max = z_min + 50
    # Filtreleme sınırları
    y_min2, y_max2 = y_min + 70, y_max + 90
    z_min2, z_max2 = z_min + 62, z_max + 75

    # Merkezi X ekseni bul
    x_center = (np.max(points[:, 0]) + np.min(points[:, 0])) / 2
    delta_x = 1

    # Filtreleme işlemleri
    filtered_points = points[(points[:, 1] > y_min) &
                             (points[:, 1] < y_max) &
                             (points[:, 2] > z_min) &
                             (points[:, 2] < z_max)]

    filtered_points2 = points[(points[:, 1] > y_min2) &
                              (points[:, 1] < y_max2) &
                              (points[:, 2] > z_min) &
                              (points[:, 2] < z_max)]

    filtered_points3 = points[(points[:, 2] > z_min2) &
                              (points[:, 2] < z_max2)]

    end = points[(points[:, 0] > x_center - delta_x) &
                 (points[:, 0] < x_center + delta_x)]

    end_length = points[(points[:, 1] > np.min(end[:, 1])) &
                        (points[:, 1] < np.min(filtered_points[:, 1]))]

    # Boş veri kontrolü
    if filtered_points.size == 0 or filtered_points2.size == 0 or filtered_points3.size == 0:
        print("Uyarı: Filtrelenmiş nokta bulutlarından biri boş!")

    # Filtrelenmiş noktaları PointCloud olarak kaydet
    # def save_filtered_point_cloud(points_array, file_path):
    #     if points_array.size > 0:
    #         pcd = o3d.geometry.PointCloud()
    #         pcd.points = o3d.utility.Vector3dVector(points_array)
    #         o3d.io.write_point_cloud(file_path, pcd)
    #     else:
    #         print(f"'{file_path}' boş bir veri içeriyor, kaydedilmedi.")
            
    # Filtrelenmiş noktaları kaydet
    # save_filtered_point_cloud(filtered_points, "filtered_points.ply")
    # save_filtered_point_cloud(filtered_points2, "filtered_points2.ply")
    # save_filtered_point_cloud(filtered_points3, "filtered_points3.ply")
    # save_filtered_point_cloud(end_length, "end_points.ply")
    

    l_248 = b_vertical-np.min(end_length[:,1])
    print("l_248",l_248)
    return l_248
