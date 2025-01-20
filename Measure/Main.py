from tkinter.messagebox import showerror
from MecheyePackage.robot_control import send_command
from Scripts import *
from MecheyePackage import TriggerWithExternalDeviceAndFixedRate, robot
import open3d as o3d
import numpy as np
import matplotlib
matplotlib.use('Agg')
import time
import pandas as pd

def rotate_point_cloud(points, angle_degrees, rot):
    """
    Bir nokta bulutunu Z ekseni etrafında belirli bir açıyla döndür.
    :param points: Nx3 boyutunda numpy dizisi (nokta bulutu)
    :param angle_degrees: Döndürme açısı (derece cinsinden)
    :return: Döndürülmüş nokta bulutu (Nx3 numpy dizisi)
    """
    # Dereceden radyana çevir
    angle_radians = np.radians(angle_degrees)
    
    # Z ekseni etrafında dönüşüm matrisi
    if rot == "z":
        
        rotation_matrix = np.array([
        [np.cos(angle_radians), -np.sin(angle_radians), 0],
        [np.sin(angle_radians),  np.cos(angle_radians), 0],
        [0, 0, 1]
    ])
    elif rot == "x":

        rotation_matrix = np.array([
        [1, 0, 0],
        [0, np.cos(angle_radians), -np.sin(angle_radians)],
        [0, np.sin(angle_radians), np.cos(angle_radians)]
    ])
    elif rot == "y":
            
        rotation_matrix = np.array([
        [np.cos(angle_radians), 0, np.sin(angle_radians)],
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

def remove_gripper_points(points):
    """
    Belirtilen Y ekseni aralığında yer alan noktaları bir nokta bulutundan siler.

    Args:
        point_cloud (o3d.geometry.PointCloud): Giriş nokta bulutu.
        y_min (float): Silinecek aralığın alt sınırı (dahil).
        y_max (float): Silinecek aralığın üst sınırı (dahil).

    Returns:
        o3d.geometry.PointCloud: Filtrelenmiş nokta bulutu.
    """
    min_x = np.min(points[:, 0])
    
    y_min, y_max = np.min(points[:,1][points[:,0] < min_x+23]), np.max(points[:,1][points[:,0] < min_x+23])
    # Y ekseni değerine göre filtreleme
    filtered_points = points[(points[:, 1] < y_min) | (points[:, 1] > y_max)]

    return filtered_points


# Initialize Mech-Eye profiler with external device and fixed rate trigger
mech_eye = TriggerWithExternalDeviceAndFixedRate()

rotated_pcd = o3d.geometry.PointCloud()

# Data storage list for Excel
results = []

for i in range(1):
    start_time = time.time()
    send_command({"cmd": 107, "data": {"content": "ResetAllError()"}})
    send_command({"cmd": 303, "data": {"mode": "0"}})
    send_command({"cmd": 105, "data": {"name": "pick.lua"}})
    send_command({"cmd": 101, "data": {}})
    send_command({"cmd": 303, "data": {"mode": "1"}})
    
    time.sleep(10)

    scrc = [-5.9326171875, -74.58998878403466, 91.40015857054455, -196.742946511448, 5.83406656095297, 89.98324856899752]
    ret = robot.MoveJ(scrc, 0, 0, vel=100)

    small = mech_eye.main(lua_name="small.lua")
    small = rotate_point_cloud(small, 90, "z")
    small= small[small[:,0]<np.min(small[:,0])+50]
    rotated_pcd.points = o3d.utility.Vector3dVector(small)
    o3d.io.write_point_cloud("/home/eypan/Documents/scanner/jaguar_measure/small.ply", rotated_pcd)

    circle_fitter = CircleFitter(small)
    s_datum = circle_fitter.get_datum()
    print("s_datum", s_datum) 
    horizontal = mech_eye.main(lua_name="horizontal.lua")
    horizontal = rotate_point_cloud(horizontal, -90, "z")
    rotated_pcd.points = o3d.utility.Vector3dVector(horizontal)
    o3d.io.write_point_cloud("/home/eypan/Documents/scanner/jaguar_measure/horizontal.ply", rotated_pcd)

    l_7_1 = filter_and_visualize_projection_with_ply(horizontal)
    l_40 = get_40(horizontal)

    circle_fitter = CircleFitter(horizontal)
    circle, circle2= circle_fitter.fit_circles_and_plot()
    feature_2 = circle2[2]
    vertical = mech_eye.main(lua_name="vertical.lua")
    send_command({"cmd": 204, "data": {"content": "SetDO(7,0,0)"}})
    vertical = remove_gripper_points(vertical)
    rotated_pcd.points = o3d.utility.Vector3dVector(vertical)
    o3d.io.write_point_cloud("/home/eypan/Documents/scanner/jaguar_measure/vertical.ply", rotated_pcd)


    x_median = np.median(vertical[:, 0])
    y_min = np.min(vertical[:, 1])  # y_min değerini hesaplayın (veya tanımlayın)

    mask = (
        (vertical[:, 0] >= x_median - 2) & (vertical[:, 0] <= x_median + 2) &
        (vertical[:, 1] >= y_min) & (vertical[:, 1] <= y_min + 3)
    )
    z_max_in_window = np.max(vertical[mask, 2])

    datum_trans_val = z_max_in_window - circle_fitter.max_y_strip()
    datum_vertical = s_datum + datum_trans_val
    print("datum_vertical", datum_vertical)

    l_17_2, _ = horn_diff(vertical)
    l_23_4, _ = horn_diff(vertical, 240, 280)

    B = circle_fitter.get_B()
    b_trans_val = np.max(vertical[:, 1]) - np.max(horizontal[:, 2])
    b_vertical = B + b_trans_val


    _, center_z, radius_big = bigcircle(vertical, crc=True)
    _, _, radius_small = bigcircle(vertical, "small_circle", val_x=0.90, val_y=0.2, val_z=0.05, crc=True)

    _, _, r1, l_79_73 = kaydırak(vertical, b_vertical)
    z_trans_val = circle[1] - center_z
    datum = circle_fitter.get_datum()
    datum_vertical = datum - z_trans_val

    _, _, r2, _ = kaydırak(vertical, datum_vertical=datum_vertical, y_divisor=0.11, crc_l=27)

    l_42 = np.max(vertical[:, 1]) - b_vertical
    l_248 = arm_horn_lengths(vertical, b_vertical)

    processing_time = time.time() - start_time

    # Append results for this iteration
    
    results.append({
        "Feature1": False,
        "Feature2 (25mm/2)": feature_2,
        "Feature3": False,
        "Feature4 (25mm/2)": radius_small,
        "Feature5 (L40)": l_40,
        "Feature6 (L248)": l_248,
        "Feature7 (L42)": l_42,
        "Feature8 (L79.73)": l_79_73,
        "Feature8 (R1-62.5)": r1,
        "Feature8 (R2-22.5)": r2,
        "Feature9 (3mm)": "feature9_3mm",
        "Feature10 (88.6)": False,
        "Feature11 (10.6)": False,
        "Feature12 (81.5)": False,
        "Feature13 (L23.4)": l_23_4,
        "Feature14 (L17.2)": l_17_2,
        "Feature15 (2C)": False,
        "Processing Time (s)": processing_time
    })

# Save results to an Excel file
output_file = "/home/eypan/Documents/scanner/jaguar_measure/scan_results.xlsx"

# Transform results with iteration tracking
rows = []
for iteration, result in enumerate(results, start=1):
    for name, value in result.items():
        rows.append({"iteration": iteration, "name": name, "value": value})

# Create DataFrame with 'iteration', 'name', and 'value' columns
results_df = pd.DataFrame(rows)

# Save the DataFrame to Excel
try:
    with pd.ExcelWriter(output_file, mode='w', engine='openpyxl') as writer:
        results_df.to_excel(writer, index=False, header=True, sheet_name="ScanResults")
except FileNotFoundError:
    # Handle any path issues if the directory doesn't exist
    print(f"Error: Could not find the directory for {output_file}. Check the path and try again.")

print("Results successfully saved to Excel.")


