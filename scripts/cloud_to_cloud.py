import os
import subprocess
import numpy as np
import open3d as o3d

# Nokta bulutlarını yükleme
cloud1_path = "/home/rog/Documents/scanner/transform/vertical.ply"
cloud2_path = "/home/rog/Documents/scanner/transform/vertical1.ply"

cloud1 = o3d.io.read_point_cloud(cloud1_path)
cloud2 = o3d.io.read_point_cloud(cloud2_path)

# SOR filtresi uygulama (cloud1 için)
print("SOR filtresi uygulanıyor...")
cl, ind = cloud1.remove_statistical_outlier(nb_neighbors=20, std_ratio=1.0)
cloud1_filtered = cloud1.select_by_index(ind)

# Filtrelenmiş bulutu kaydetme
filtered_cloud1_path = "/home/rog/Documents/scanner/transform/scripts/corrupt_filtered.ply"
o3d.io.write_point_cloud(filtered_cloud1_path, cloud1_filtered)
print(f"SOR filtresi sonrası nokta bulutu kaydedildi: {filtered_cloud1_path}")

# Filtrelenmiş bulutu numpy array'e dönüştürme
points1 = np.asarray(cloud1_filtered.points)
points2 = np.asarray(cloud2.points)

# Y eksenindeki sınır değerleri
y_min = min(np.min(points1[:, 1]), np.min(points2[:, 1]))
y_max = max(np.max(points1[:, 1]), np.max(points2[:, 1]))

# Y eksenini 4 eşit aralığa bölme
y_splits = np.linspace(y_min, y_max, 5)  # 4 aralık, 5 sınır

# Parçaları oluşturma
def split_cloud(points, y_splits):
    parts = []
    for i in range(len(y_splits) - 1):
        part = points[(points[:, 1] >= y_splits[i]) & (points[:, 1] < y_splits[i + 1])]
        parts.append(part)
    return parts

parts1 = split_cloud(points1, y_splits)
parts2 = split_cloud(points2, y_splits)

# Parçaları kaydetme
output_dir = "/home/rog/Documents/scanner/transform/scripts/split_parts"
os.makedirs(output_dir, exist_ok=True)

def save_parts(parts, prefix):
    paths = []
    for idx, part in enumerate(parts):
        pc = o3d.geometry.PointCloud()
        pc.points = o3d.utility.Vector3dVector(part)
        filename = os.path.join(output_dir, f"{prefix}_part_{idx + 1}.ply")
        o3d.io.write_point_cloud(filename, pc)
        paths.append(filename)
    return paths

cloud1_parts_paths = save_parts(parts1, "cloud1_filtered")
cloud2_parts_paths = save_parts(parts2, "cloud2")

# CloudCompare komutlarını çalıştırma
cloudcompare_path = "/usr/bin/CloudCompare"  # CloudCompare uygulamasının doğru yolu

for i in range(4):  # Her bir parça için
    reference_path = cloud1_parts_paths[i]
    target_path = cloud2_parts_paths[i]
    output_log = os.path.join(output_dir, f"distance_analysis_part_{i + 1}.txt")
    difference_file = os.path.join(output_dir, f"part_{i + 1}_C2C_DIST.ply")

    command = [
        cloudcompare_path,
        "-SILENT",
        "-C_EXPORT_FMT", "PLY",
        "-LOG_FILE", output_log,
        "-O", reference_path,
        "-O", target_path,
        "-C2C_DIST"
    ]

    # CloudCompare çalıştırma
    try:
        subprocess.run(command, check=True)
        print(f"Parça {i + 1} için CloudCompare işlemi tamamlandı.")
    except subprocess.CalledProcessError as e:
        print(f"Parça {i + 1} için CloudCompare işleminde bir hata oluştu: {e}")

    # Log dosyasını analiz etme
    if os.path.exists(output_log):
        with open(output_log, "r") as log_file:
            log_content = log_file.readlines()
            print(f"Parça {i + 1} için metrikler:")
            for line in log_content:
                if "Min dist." in line or "Max dist." in line or "Avg dist." in line or "Sigma" in line or "Max error" in line:
                    print(line.strip())

    # Farklılık bölgeleri dosyasını kontrol etme
    if os.path.exists(difference_file):
        print(f"Parça {i + 1} için farklılık bölgeleri dosyası oluşturuldu: {difference_file}")
    else:
        print(f"Parça {i + 1} için farklılık bölgeleri dosyası bulunamadı.")
