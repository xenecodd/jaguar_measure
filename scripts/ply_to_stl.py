import open3d as o3d
import numpy as np
import trimesh
import subprocess

subprocess.run(["pcl_converter", "/home/eypan/Documents/down_jaguar/jaguar_measure/mstfhc.ply", "output_ascii.ply", "0"])

def downsample_ply(input_ply, output_ply, sample_ratio=0.5):
    # PLY dosyasını yükle
    mesh = trimesh.load(input_ply)
    if not hasattr(mesh, "vertices"):
        print("Dosya nokta bulundurmadığı için işlenemiyor.")
        return
    
    points = np.array(mesh.vertices)
    
    # Örnekleme oranına göre noktaları azalt
    num_samples = int(len(points) * sample_ratio)
    sampled_indices = np.random.choice(len(points), num_samples, replace=False)
    downsampled_points = points[sampled_indices]

    # Yeni nokta bulutunu kaydet
    downsampled_mesh = trimesh.Trimesh(vertices=downsampled_points)
    downsampled_mesh.export(output_ply)

    print(f"Orijinal nokta sayısı: {len(points)}")
    print(f"Azaltılmış nokta sayısı: {len(downsampled_points)}")
    print(f"Azaltılmış dosya kaydedildi: {output_ply}")

downsample_ply("/home/eypan/Documents/down_jaguar/jaguar_measure/output_ascii.ply", "downsampled.ply", sample_ratio=0.8)

# 2. Nokta bulutunu dosyadan okuyun
pcd = o3d.io.read_point_cloud("downsampled.ply")

# Dosyanın başarıyla açılıp açılmadığını kontrol edin
if len(pcd.points) == 0:
    raise ValueError(f"Nokta bulutu boş ya da dosya açılamadı: downsampled.ply")

print(f"{len(pcd.points)} adet nokta okundu.")

# 3. Nokta bulutunun normallerini hesaplayın (Poisson Reconstruction için gerekli)
pcd.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.05, max_nn=30))

# (Opsiyonel) Nokta bulutunu görselleştirmek için:
# o3d.visualization.draw_geometries([pcd])

# 4. Poisson Reconstruction ile mesh oluşturun
print("Poisson Reconstruction başlatılıyor...")
mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(pcd, depth=16)
print("Poisson Reconstruction tamamlandı.")

# 5. Oluşan mesh üzerinde düşük yoğunluklu bölgeleri filtreleyin (isteğe bağlı)
densities = np.asarray(densities)
vertices_to_remove = densities < np.quantile(densities, 0.2)
mesh.remove_vertices_by_mask(vertices_to_remove)

# 6. Mesh normallerini hesaplayın (STL yazımı için gerekli olabilir)
mesh.compute_vertex_normals()

# 7. Mesh'i STL dosyası olarak kaydedin
output_file = "/home/eypan/Documents/down_jaguar/jaguar_measure/model2.stl"
o3d.io.write_triangle_mesh(output_file, mesh)
print("Mesh STL dosyası olarak kaydedildi:", output_file)

# (Opsiyonel) Oluşan mesh'i görselleştirmek için:
# o3d.visualization.draw_geometries([mesh])
