import open3d as o3d

# Nokta bulutunu yükle
pcd = o3d.io.read_point_cloud("/home/rog/Documents/scanner/transform/build/merged_scan_no_icp.pcd")

pcd.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.1, max_nn=30))

# Greedy Projection Triangulation
mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_alpha_shape(pcd, alpha=0.1)

# Mesh'i görselleştir
o3d.visualization.draw_geometries([mesh])
