import numpy as np
import open3d as o3d

# Point cloud verisini yükleyin
cloud = '/home/rog/Documents/scanner/transform/reference_cloud_jaguar.ply'
cloud = o3d.io.read_point_cloud(cloud)

# Point cloud verisini numpy array olarak alın
points = np.asarray(cloud.points)

# Merkez koordinatlarını hesaplayın
center_x = np.mean(points[:, 0])
center_y = np.mean(points[:, 1])
center_z = np.mean(points[:, 2])

# X ekseninde yansıma yapın
points[:, 0] = 2 * center_x - points[:, 0]

# Yeni point cloud oluşturun
new_cloud = o3d.geometry.PointCloud()
new_cloud.points = o3d.utility.Vector3dVector(points)

# Yeni point cloud'u kaydedin
o3d.io.write_point_cloud('/home/rog/Documents/scanner/transform/test/mirrored_point_cloud.pcd', new_cloud)
