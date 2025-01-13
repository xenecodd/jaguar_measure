import subprocess

# CloudCompare komut satırı parametreleri
input_file = "/home/rog/Documents/scanner/transform/ransac/181.ply"
output_file = "/home/rog/Documents/scanner/transform/ransac/filtered_output.ply"

mean_k = 6  # Kümelenmiş komşular sayısı
stddev_mul = 1.0  # Standart sapma çarpanı

# CloudCompare komutunu oluşturun
cloudcompare_command = [
    "CloudCompare",  # CloudCompare'in komut satırı komutu
    "-SILENT",  # Çıktıyı gizlemek için
    "-O", input_file,  # Giriş dosyasını yükle
    "-SOR",  # SOR filtreleme
    f"-SOR_K {mean_k}",  # Mean K değeri
    f"-SOR_MUL {stddev_mul}",  # Standart sapma çarpanı
    "-SAVE", output_file  # Çıktıyı kaydet
]

# CloudCompare komutunu çalıştır
subprocess.run(cloudcompare_command)

print(f"SOR filtresi uygulandı ve çıktı {output_file} dosyasına kaydedildi.")
