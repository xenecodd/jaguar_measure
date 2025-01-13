import open3d as o3d
import numpy as np
import matplotlib.pyplot as plt

# Mesh'i yükleyin
mesh_path = "/home/rog/Documents/scanner/transform/T9P3-10T800-A-INS-01 FOAM BRACKET TYPE 01 FEV 16.1 Frozen.stl"  # Mesh dosyasının yolu
mesh = o3d.io.read_triangle_mesh(mesh_path)

# Mesh'i noktalar kümesine dönüştürme
# Poisson disk örnekleme ile
point_cloud = mesh.sample_points_poisson_disk(number_of_points=100000)

# Nokta bulutunu görselleştirin
o3d.visualization.draw_geometries([point_cloud])

# Nokta bulutunu PLY formatında kaydetme
output_path = "/home/rog/Documents/scanner/transform/reference_cloud_jaguar.ply"  # Kaydetmek istediğiniz dosya yolu
o3d.io.write_point_cloud(output_path, point_cloud)

print(f"Nokta bulutu kaydedildi: {output_path}")
