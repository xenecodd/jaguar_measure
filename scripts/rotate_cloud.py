import open3d as o3d
import numpy as np

# .ply dosyasını yükleme
input_file = "/home/rog/Documents/scanner/transform/reference_cloud_jaguar.ply"  # Girdi dosyasının adı
output_file = "reference_cloud_90_min_to_origin.ply"  # Çıktı dosyasının adı

# Nokta bulutunu okuma
point_cloud = o3d.io.read_point_cloud(input_file)

# Z ekseninde 90 derece döndürme matrisi
rotation_matrix = np.array([
    [np.cos(-(np.pi / 2)), -np.sin(-(np.pi / 2)), 0],
    [np.sin(-(np.pi / 2)),  np.cos(-(np.pi / 2)), 0],
    [0,                  0,                 1]
])

# Nokta bulutunu döndürme
point_cloud.rotate(rotation_matrix, center=(0, 0, 0))

# Nokta bulutunun min değerlerini hesaplama
points = np.asarray(point_cloud.points)
min_corner = points.max(axis=0)

# Min köşeyi orijine taşımak için her noktayı kaydırma
points -= min_corner
point_cloud.points = o3d.utility.Vector3dVector(points)

# Döndürülmüş ve taşınmış noktaları bir dosyaya kaydetme
o3d.io.write_point_cloud(output_file, point_cloud)

print(f"Nokta bulutu başarıyla '{output_file}' dosyasına kaydedildi!")
