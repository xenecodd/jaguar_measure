import numpy as np
import open3d as o3d
import matplotlib.pyplot as plt
from scipy.optimize import leastsq

# Dosya yolu
file_path = "/home/rog/Documents/scanner/transform/scripts/merged_clouds_new.ply"

# Nokta bulutunu yükleyin
pcd = o3d.io.read_point_cloud(file_path)

# Nokta bulutunu numpy dizisine çevir
points = np.asarray(pcd.points)
points[:,1] = -points[:,1]  # Y ekseninin ters çevrilmesi

# Nokta bulutunun her eksendeki min ve max değerlerini hesapla
x_min_val, x_max_val = np.min(points[:, 0]), np.max(points[:, 0])
y_min_val, y_max_val = np.min(points[:, 1]), np.max(points[:, 1])
z_min_val, z_max_val = np.min(points[:, 2]), np.max(points[:, 2])

# Hesaplamalar: Bölme değerlerini kullanarak filtreleme parametrelerini dinamik hale getirme
y_divisor = 0.261724137
z_divisor = 0.06324472

y_min = y_min_val + (y_divisor * (y_max_val - y_min_val))
y_max = y_min + 20
print(f"y_min: {y_min}, y_max: {y_max}")

x_center = ((x_min_val + x_max_val) / 2) - 15
delta_y = 0.5  # Kesit genişliği, ayarlayabilirsiniz
print(f"x_center: {x_center}, delta_y: {delta_y}")

z_min = z_min_val + (z_divisor * (z_max_val - z_min_val))
z_max = z_min + 60
print(f"z_min: {z_min}, z_max: {z_max}")

# Filtreleme işlemi
filtered_points = points[(points[:, 0] > x_center - delta_y) & 
                         (points[:, 0] < x_center + delta_y) & 
                         (points[:, 1] > y_min) & 
                         (points[:, 1] < y_max) & 
                         (points[:, 2] > z_min) & 
                         (points[:, 2] < z_max)]

# Filtrelenmeyen noktalar
remaining_points = points[~((points[:, 0] > x_center - delta_y) & 
                             (points[:, 0] < x_center + delta_y) & 
                             (points[:, 1] > y_min) & 
                             (points[:, 1] < y_max) & 
                             (points[:, 2] > z_min) & 
                             (points[:, 2] < z_max))]

# Nokta bulutunu X-Z düzlemine projekte et
def project_to_xz_plane(points):
    return points[:, [1, 2]]  # X ve Z koordinatlarını al

# Filtrelenmiş ve filtrelenmeyen noktaları projekte et
projected_filtered = project_to_xz_plane(filtered_points)
projected_remaining = project_to_xz_plane(remaining_points)

# X ve Z koordinatlarını ayır
x_2d, z_2d = projected_filtered[:, 0], projected_filtered[:, 1]
x_remaining_2d, z_remaining_2d = projected_remaining[:, 0], projected_remaining[:, 1]

# Çember fitting için fonksiyonlar
def calc_radius(xc, yc, x, y):
    return np.sqrt((x - xc)**2 + (y - yc)**2)

def cost_function(params, x, y):
    xc, yc, r = params
    return calc_radius(xc, yc, x, y) - r

# Başlangıç tahmini
def initial_guess(x, y):
    xc = np.mean(x)
    yc = np.mean(y)
    r = np.mean(np.sqrt((x - xc)**2 + (y - yc)**2))
    return [xc, yc, r]

# Başlangıç tahmini
guess = initial_guess(x_2d, z_2d)
print(f"Başlangıç tahmini - Merkez: ({guess[0]:.2f}, {guess[1]:.2f}), Yarıçap: {guess[2]:.2f}")

# Çember fitting işlemi (Dış çember)
result, _ = leastsq(cost_function, guess, args=(x_2d, z_2d))
xc, yc, r_outer = result
print(f"Çemberin merkezi: ({xc:.2f}, {yc:.2f}), Yarıçap: {r_outer:.2f}")

# 3D görselleştirme
def visualize_3d(filtered_points, remaining_points, xc, yc, r_outer):
    # Open3D kullanarak görselleştirme
    filtered_pcd = o3d.geometry.PointCloud()
    filtered_pcd.points = o3d.utility.Vector3dVector(filtered_points)
    filtered_pcd.paint_uniform_color([0, 0, 1])  # Mavi renkte filtrelenmiş noktalar

    remaining_pcd = o3d.geometry.PointCloud()
    remaining_pcd.points = o3d.utility.Vector3dVector(remaining_points)
    remaining_pcd.paint_uniform_color([1, 0, 0])  # Kırmızı renkte filtrelenmeyen noktalar

    # Çemberin parametrik denklemi için 3D çember
    theta = np.linspace(0, 2 * np.pi, 100)
    x_circle = xc + r_outer * np.cos(theta)
    z_circle = yc + r_outer * np.sin(theta)
    y_circle = np.full_like(x_circle, (y_min + y_max) / 2)  # Çemberin y düzleminde merkezi

    circle_points = np.vstack((x_circle, y_circle, z_circle)).T
    circle_pcd = o3d.geometry.PointCloud()
    circle_pcd.points = o3d.utility.Vector3dVector(circle_points)
    circle_pcd.paint_uniform_color([0, 1, 0])  # Yeşil renkte çember

    # Işık ekleyerek 3D görselleştirme yapalım
    vis = o3d.visualization.Visualizer()
    vis.create_window()
    vis.add_geometry(filtered_pcd)
    vis.add_geometry(remaining_pcd)
    vis.add_geometry(circle_pcd)
    
    # Işıklandırma ayarları
    render_option = vis.get_render_option()
    render_option.point_size = 2  # Nokta boyutunu ayarla
    render_option.light_on = True  # Işıklandırma aç
    render_option.background_color = np.asarray([0.1, 0.1, 0.1])  # Arka plan rengi

    # Kamera ayarları
    view_control = vis.get_view_control()
    view_control.set_front([0, -1, 0])
    view_control.set_lookat([xc, (y_min + y_max) / 2, yc])
    view_control.set_up([0, 0, 1])
    view_control.set_zoom(0.8)

    # Görselleştirme penceresini göster
    vis.run()
    vis.destroy_window()

# Görselleştir
visualize_3d(filtered_points, remaining_points, xc, yc, r_outer)
