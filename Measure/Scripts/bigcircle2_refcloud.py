# process_point_cloud.py
import numpy as np
import open3d as o3d
import matplotlib.pyplot as plt
from scipy.optimize import leastsq

# Çember fitting fonksiyonları
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


def bigcircle(pcd,name="big circle 90",val_x=0.00310344,val_y = 0.125, val_z = 0.796, crc=False,crc2=False):
    points = np.zeros_like(pcd)
    points[:, 1] = pcd[:, 0]
    points[:, 0] = -pcd[:, 1]
    points[:, 2] = pcd[:, 2]
    
    # max_x, max_y, max_z = np.max(points, axis=0)
    # min_x, min_y, min_z = np.min(points, axis=0)
    # points -= [min_x, max_y, max_z]  # Yani her noktanın x, y ve z koordinatlarından min_x, min_y, min_z çıkarılır
    # -96 35derece ve -67 90derece
    # Nokta bulutunun her eksendeki min ve max değerlerini hesapla
    min_y, max_y = np.min(points[:, 1]), np.max(points[:, 1])
    min_x, max_x = np.min(points[:, 0]), np.max(points[:, 0])
    min_z, max_z = np.min(points[:, 2]), np.max(points[:, 2])

    # Hesaplamalar: Bölme değerlerini kullanarak filtreleme parametrelerini dinamik hale getirme
    x_min = (min_x + val_x * (max_x - min_x))
    x_max = x_min + 10
    y_min = min_y + val_y * (max_y - min_y)
    y_max = y_min + 30
    z_min = min_z + val_z * (max_z - min_z)
    z_max = z_min + 10

    # İlk filtreleme
    filtered_points = points[(points[:, 0] > x_min) &
                             (points[:, 0] < x_max) &
                             (points[:, 1] > y_min) &
                             (points[:, 1] < y_max) &
                             (points[:, 2] > z_min) &
                             (points[:, 2] < z_max)]

    # X-Z düzlemine projekte edilen noktalar
    projected_points_2d = filtered_points[:, [1, 2]]
    
    x_2d, z_2d = projected_points_2d[:, 0], projected_points_2d[:, 1]

    try:
        if (crc==True):
            # İlk çember fitting işlemi
            outer_guess = initial_guess(x_2d, z_2d)
            outer_result, _ = leastsq(cost_function, outer_guess, args=(x_2d, z_2d))
            xc_outer, zc_outer, r_outer = map(float, outer_result)

            # Çember bilgilerini yazdır
            center = (xc_outer, zc_outer)
            radius = r_outer

            # Çemberi çizim
            theta = np.linspace(0, 2 * np.pi, 100)
            x_outer_circle = xc_outer + r_outer * np.cos(theta)
            z_outer_circle = zc_outer + r_outer * np.sin(theta)

            # plt.figure(figsize=(8, 8))
            # plt.scatter(x_2d, z_2d, s=1, color='blue', label='Noktalar')
            # plt.plot(x_outer_circle, z_outer_circle, color='red', label=f'Çember (R = {radius:.2f})')

            # plt.title("X-Z Düzleminde Nokta Bulutu ve Çember Fitting (Circle 1)")
            # plt.xlabel("X")
            # plt.ylabel("Z")
            # plt.axis('equal')
            # plt.legend()
            # plt.show()
            # save_point_cloud("/home/rog/Documents/scanner/transform/unflt_frst.ply", points)
            # save_3d_filter_box_as_point_cloud("/home/rog/Documents/scanner/transform/frst_crc.ply", x_min, x_max, y_min, y_max,zc_outer,zc_outer+5)
            print(f"{name} merkezi: ({center[0]:.2f}, {center[1]:.2f}), Yarıçap: {radius:.2f}")
            return center[0],center[1],radius
        if(crc2==True):
            # Eğer zc_outer sağlanmışsa, 2. çember için filtreleme yapılacak
            if zc_outer is None:
                raise ValueError("zc_outer parametresi 2. çember için gereklidir.")
            filtered_points2 = points[(points[:, 0] > x_min) &
                                       (points[:, 0] < x_max) &
                                       (points[:, 1] > y_min) &
                                       (points[:, 1] < y_max) &
                                       (points[:, 2] > zc_outer) &
                                       (points[:, 2] < zc_outer+5)]
            if filtered_points2.shape[0] == 0:
                print("Filtrelenmiş noktalar boş. Çember fitting yapılamıyor.")

            save_3d_filter_box_as_point_cloud("/home/rog/Documents/scanner/transform/sec_crc.ply", x_min, x_max, y_min, y_max, zc_outer, zc_outer+5)
            save_point_cloud("/home/rog/Documents/scanner/transform/unflt_sec.ply", points)
            print("2. çember yükseklik:", zc_outer[0])

            # X-Z düzlemine projekte edilen noktalar
            projected_points_2d = filtered_points2[:, [0, 1]]
            x_2d_2, z_2d_2 = projected_points_2d[:, 0], projected_points_2d[:, 1]

            # 2. Çember fitting işlemi
            outer_guess_2 = initial_guess(x_2d_2, z_2d_2)
            outer_result_2, _ = leastsq(cost_function, outer_guess_2, args=(x_2d_2, z_2d_2))
            xc_outer_2, zc_outer_2, r_outer_2 = map(float, outer_result_2)

            # Çember bilgilerini yazdır
            center_2 = (xc_outer_2, zc_outer_2)
            radius_2 = r_outer_2

            # Çemberi çizim
            theta_2 = np.linspace(0, 2 * np.pi, 100)
            x_outer_circle_2 = xc_outer_2 + r_outer_2 * np.cos(theta_2)
            z_outer_circle_2 = zc_outer_2 + r_outer_2 * np.sin(theta_2)

            # plt.figure(figsize=(8, 8))
            # plt.scatter(x_2d_2, z_2d_2, s=1, color='blue', label='Noktalar')
            # plt.plot(x_outer_circle_2, z_outer_circle_2, color='red', label=f'Çember (R = {radius_2:.2f})')

            # plt.title("X-Z Düzleminde Nokta Bulutu ve Çember Fitting (Circle 2)")
            # plt.xlabel("X")
            # plt.ylabel("Z")
            # plt.axis('equal')
            # plt.legend()
            # plt.show()

            print(f"Çemberin merkezi (filtered_points2): ({center_2[0]:.2f}, {center_2[1]+28:.2f}), Yarıçap: {radius_2:.2f}")

        else:
            print("Geçersiz çember numarası! Lütfen 1 veya 2 seçiniz.")
    except Exception as e:
        print(f"Çember fitting işlemi sırasında hata oluştu: {e}")


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

