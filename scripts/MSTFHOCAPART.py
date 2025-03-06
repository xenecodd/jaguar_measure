import numpy as np
import open3d as o3d
import matplotlib.pyplot as plt
import cv2
from scipy.optimize import leastsq

def get_scale():
    return 12

def upscale_points(points, scale, image_size=(500, 500)):
    """
    Verilen 2D noktaları, belirtilen ölçek ve image_size ile bir boş görüntüye çizer.
    """
    upscale_size = (image_size[0] * scale, image_size[1] * scale)
    image = np.zeros(upscale_size, dtype=np.uint8)
    for x, y in points:
        # Noktaları ölçeklendirip tam sayıya çeviriyoruz.
        xi, yi = int(x * scale), int(y * scale)
        if 0 <= xi < upscale_size[1] and 0 <= yi < upscale_size[0]:
            cv2.circle(image, (xi, yi), radius=2, color=255, thickness=-3)
    return image

def detect_edges(image):
    blurred = cv2.GaussianBlur(image, (31, 31), 0)
    edges = cv2.Canny(blurred, 150, 200)
    return edges

def process_and_visualize(points):
    high_res_image = upscale_points(points, scale=get_scale())
    edges = detect_edges(high_res_image)
    edge_coords = np.column_stack(np.where(edges > 0))
    return edge_coords

def generate_circle_points(center, radius, num_points=100):
    angles = np.linspace(0, 2 * np.pi, num_points)
    x = center[0] + radius * np.cos(angles)
    y = center[1] + radius * np.sin(angles)
    return x, y

def fit_circle(x, y):
    def cost_function(params, x, y):
        xc, yc, r = params
        return np.sqrt((x - xc)**2 + (y - yc)**2) - r
    guess = [np.mean(x), np.mean(y), np.mean(np.sqrt((x - np.mean(x))**2 + (y - np.mean(y))**2))]
    result, _ = leastsq(cost_function, guess, args=(x, y))
    return result

# ---------------------------
# 1. Noktaları Oku ve ROI'yi Belirle
# ---------------------------
pcd = o3d.io.read_point_cloud("mstfhc.ply")
points = np.asarray(pcd.points)

# Z ekseni için bir eşik (örneğin, zmax-2)
zmax = np.max(points[:, 2])
points_in_range = points[points[:, 2] >= (zmax - 2)]
ymax = np.max(points[:, 1])
if len(points_in_range) > 0:
    ymax_new = np.min(points_in_range[:, 1])
else:
    ymax_new = ymax

xmax = np.max(points[:, 0])
print(f"Güncellenmiş Ymax: {ymax_new:.2f}")

# ROI: Örneğin, x: 50-80, y: 200-230, ve z: zmax-6'dan büyük
filtered_points = points[(points[:, 0] >= 50) & (points[:, 0] <= 80) &
                         (points[:, 1] >= 200) & (points[:, 1] <= 230) &
                         (points[:, 2] > zmax - 6)]

# ROI'nin x-y projeksiyonu (ölçeklenmemiş)
projected_points_2d = filtered_points[:, [0, 1]]

# Çember uydurma için, ROI'nin kenar noktalarını elde ediyoruz
edge_coords = process_and_visualize(projected_points_2d)
x_edge = edge_coords[:, 1] / get_scale()  # ilk sütun: x (kolonlar ve satırlar ters)
y_edge = edge_coords[:, 0] / get_scale()

# Çember uydurma: Kenar noktalarından çemberin merkezini ve yarıçapını hesaplıyoruz
center_x, center_y, radius = fit_circle(x_edge, y_edge)
print(f"Çember Merkezi: ({center_x:.2f}, {center_y:.2f}), Yarıçap: {radius:.2f}")
print("Up:", ymax_new - center_y)
print("Right:", xmax - center_x)

# ---------------------------
# 2. Tüm Noktalar Üzerinde Edge Bulma (İç Kenar / Dış Kenar)
# ---------------------------
# Tüm noktaların x-y projeksiyonu (tüm bulut verisi)
all_points = points[(points[:,2] > zmax - 3)][:, [0, 1]]
# Not: Tüm bulut verisinin görüntüye sığması için image_size uygun seçilmeli.
# Burada örnek olarak (500, 500) kullanılıyor.
all_img = upscale_points(all_points, scale=get_scale(), image_size=(500, 500))

# Morfolojik işlemlerle kenar tespiti:
kernel = np.ones((3, 3), np.uint8)
eroded_img = cv2.erode(all_img, kernel, iterations=1)
dilated_img = cv2.dilate(all_img, kernel, iterations=1)

# İç kenar: orijinal - erozyon (iç kısımdan kayıp olan sınır)
inner_edge_img = cv2.subtract(all_img, eroded_img)
# Dış kenar: dilatasyon - orijinal (dışarı taşan sınır)
outer_edge_img = cv2.subtract(dilated_img, all_img)

# Inner edge koordinatlarını bul (satır, sütun formatında)
inner_edge_coords = np.column_stack(np.where(inner_edge_img > 0))
# Dönüştür: sütun -> x, satır -> y (ölçek geri alınır)
inner_edge_points = np.column_stack((inner_edge_coords[:, 1] / get_scale(), inner_edge_coords[:, 0] / get_scale()))

# Outer edge (sadece görselleştirme için)
outer_edge_coords = np.column_stack(np.where(outer_edge_img > 0))
outer_edge_points = np.column_stack((outer_edge_coords[:, 1] / get_scale(), outer_edge_coords[:, 0] / get_scale()))

# ---------------------------
# 3. Ölçüm Aşaması: Yalnızca İç Kenarı Kullan (Dış kenar hariç)
# ---------------------------
# Öncelikle, iç kenar noktaları arasından y ekseni ölçümü için center_x ± vertical_tolerance aralığındakileri seçelim.
vertical_tolerance = 1.0
vertical_inner_edge_points = inner_edge_points[np.abs(inner_edge_points[:, 0] - center_x) < vertical_tolerance]

# Eğer gerekiyorsa, çember merkezinin etrafındaki belirli bir yarıçap (exclusion_radius) içindeki noktaları da hariç tutalım.
exclusion_radius = 15.0  # Örneğin, 15 birim içindeki noktalar hariç tutulacak.
tolerance_circle = 1.0   # Çember uydurmada kullanılan ideal noktaların yakınlığı için tolerans

filtered_points_for_measurement = []
for pt in vertical_inner_edge_points:
    d = np.linalg.norm(pt - np.array([center_x, center_y]))
    # Eğer nokta, çember merkezinin etrafındaki exclusion_radius içindeyse, ölçüme dahil etme.
    if d < exclusion_radius:
        continue
    # Eğer nokta, çember uydurmada kullanılan ideal noktaya (yarıçap) yakın değilse dahil et.
    if abs(d - radius) > tolerance_circle:
        filtered_points_for_measurement.append(pt)
filtered_points_for_measurement = np.array(filtered_points_for_measurement)

# En yakın üst ve alt noktaları (y ekseni üzerinden) belirleyelim:
nearest_above = None
nearest_below = None
if len(filtered_points_for_measurement) > 0:
    points_above = filtered_points_for_measurement[filtered_points_for_measurement[:, 1] >= center_y]
    points_below = filtered_points_for_measurement[filtered_points_for_measurement[:, 1] <= center_y]
    
    if len(points_above) > 0:
        idx_above = np.argmin(points_above[:, 1] - center_y)
        nearest_above = points_above[idx_above]
        distance_above = nearest_above[1] - center_y
    else:
        distance_above = None

    if len(points_below) > 0:
        idx_below = np.argmin(center_y - points_below[:, 1])
        nearest_below = points_below[idx_below]
        distance_below = center_y - nearest_below[1]
    else:
        distance_below = None

    print("Çember merkezine y ekseni doğrultusunda en yakın üst nokta uzaklığı:", distance_above)
    print("Çember merkezine y ekseni doğrultusunda en yakın alt nokta uzaklığı:", distance_below)
else:
    print("Y ekseni boyunca ölçüm için yeterli nokta bulunamadı.")

# ---------------------------
# 4. Görselleştirme
# ---------------------------
# Uydurulmuş çemberin noktaları:
circle_x, circle_y = generate_circle_points((center_x, center_y), radius)

plt.figure(figsize=(12, 12))
# Tüm ROI noktaları (siyah, yarı saydam)
plt.scatter(projected_points_2d[:, 0], projected_points_2d[:, 1], color='black', s=10, alpha=0.3, label='ROI Tüm Noktalar')
# Çember uydurma için kullanılan edge noktaları (mavi)
plt.scatter(x_edge, y_edge, color='blue', s=20, alpha=0.5, label='Edge Noktaları (ROI)')
# Uydurulmuş çember (kırmızı)
plt.plot(circle_x, circle_y, color='red', linewidth=2, label='Uydurulmuş Çember')
# Çember merkezi (yeşil)
plt.scatter(center_x, center_y, color='green', marker='x', s=100, label='Çember Merkezi')
# Vertical bölge (center_x ± vertical_tolerance)
plt.axvline(x=center_x - vertical_tolerance, color='gray', linestyle='--', label='Vertical Bölge')
plt.axvline(x=center_x + vertical_tolerance, color='gray', linestyle='--')
# Tüm bulut verisinin iç kenarı (inner edge) (mor)
plt.scatter(inner_edge_points[:, 0], inner_edge_points[:, 1], color='magenta', s=15, alpha=0.7, label='İç Kenar')
# Dış kenar (outer edge) (turuncu) - sadece görselleştirme
plt.scatter(outer_edge_points[:, 0], outer_edge_points[:, 1], color='orange', s=15, alpha=0.7, label='Dış Kenar')
# Vertical bölgedeki iç kenar noktaları (cyan)
plt.scatter(vertical_inner_edge_points[:, 0], vertical_inner_edge_points[:, 1], color='cyan', marker='o', s=50, label='Vertical İç Kenar')
# Ölçüme dahil edilen noktalar (siyah büyük daire)
if len(filtered_points_for_measurement) > 0:
    plt.scatter(filtered_points_for_measurement[:, 0], filtered_points_for_measurement[:, 1],
                color='black', marker='o', s=100, label='Ölçüme Dahil Noktalar')
# En yakın üst ve alt noktalar (varsa)
if nearest_above is not None:
    plt.scatter(nearest_above[0], nearest_above[1], color='magenta', marker='D', s=150, label='En Yakın Üst Nokta')
if nearest_below is not None:
    plt.scatter(nearest_below[0], nearest_below[1], color='cyan', marker='D', s=150, label='En Yakın Alt Nokta')

plt.xlabel("X")
plt.ylabel("Y")
plt.title("Tüm Bulut Üzerinde Edge Bulma: İç Kenar (Include) - Dış Kenar (Exclude)")
plt.legend()
plt.axis("equal")
plt.show()
