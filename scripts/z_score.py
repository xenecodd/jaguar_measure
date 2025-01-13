import os
import re

# TXT dosyalarının bulunduğu klasör
output_dir = "/home/rog/Documents/scanner/transform/scripts/split_parts"
txt_files = [f for f in os.listdir(output_dir) if f.endswith(".txt")]

# Z-score hesaplama fonksiyonu
def calculate_z_scores(mean, std_dev, threshold=1):
    z_score = (threshold - mean) / std_dev
    return z_score

# TXT dosyalarını işleme
z_scores = {}
for txt_file in txt_files:
    file_path = os.path.join(output_dir, txt_file)
    with open(file_path, "r") as f:
        content = f.read()

        # Mean distance ve Std deviation değerlerini bulma
        mean_match = re.search(r"Mean distance\s*=\s*([\d.]+)", content)
        std_dev_match = re.search(r"std deviation\s*=\s*([\d.]+)", content)

        if mean_match and std_dev_match:
            mean_distance = float(mean_match.group(1))
            std_deviation = float(std_dev_match.group(1))

            # Z-score hesaplama
            z_score = calculate_z_scores(mean_distance, std_deviation)
            z_scores[txt_file] = {
                "Mean Distance": mean_distance,
                "Std Deviation": std_deviation,
                "Z-Score": z_score,
            }

# Sonuçları yazdırma
for txt_file, metrics in z_scores.items():
    print(f"{txt_file}:")
    print(f"  Mean Distance: {metrics['Mean Distance']:.6f}")
    print(f"  Std Deviation: {metrics['Std Deviation']:.6f}")
    print(f"  Z-Score: {metrics['Z-Score']:.6f}\n")
