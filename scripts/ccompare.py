import open3d as o3d

# PCD dosyasını yükleyin
pcd = o3d.io.read_point_cloud("/home/rog/Documents/scanner/transform/test/mirrored_point_cloud.pcd")

# PLY formatında kaydedin
o3d.io.write_point_cloud("/home/rog/Documents/scanner/transform/mirrored_point_cloud.ply", pcd)

print("Dosya PLY formatında kaydedildi.")
