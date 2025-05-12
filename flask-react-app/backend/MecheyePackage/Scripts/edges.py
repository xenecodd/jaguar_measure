import numpy as np
import cv2
import matplotlib.pyplot as plt
from scipy.interpolate import griddata

def get_scale():
    return 12
def upscale_points(points, scale, image_size=(500, 500)):
    """Noktaları yüksek çözünürlüklü bir görüntüye çizin."""
    upscale_size = (image_size[0] * scale, image_size[1] * scale)
    image = np.zeros(upscale_size, dtype=np.uint8)
    for x, y in points:
        x, y = int(x * scale), int(y * scale)
        if 0 <= x < upscale_size[1] and 0 <= y < upscale_size[0]:  # Sınırları kontrol et
            cv2.circle(image, (x, y), radius=1, color=255, thickness=-1)
    return image

def detect_edges(image):
    """Canny kenar algılama ile kenarları tespit edin."""
    # Daha fazla bulanıklık için kernel boyutunu artır
    blurred = cv2.GaussianBlur(image, (5, 5), 0)  # Kernel boyutunu artırdık
    # Canny kenar algılama
    edges = cv2.Canny(blurred, 150, 200)  # Optimize edilmiş eşik değerleri
    return edges


def process_and_visualize(points):
    """Noktaları işleyin ve görselleştirin."""
    # Yüksek çözünürlük için görüntüyü büyüt
    high_res_image = upscale_points(points,scale=get_scale())

    # Kenar algılama
    edges = detect_edges(high_res_image)

    # Kenarların koordinatlarını çıkar
    edge_coords = np.column_stack(np.where(edges > 0))  # Kenar piksellerinin koordinatları

    # Görselleştirme
    # plt.figure(figsize=(12, 6))
    # plt.subplot(1, 2, 1)
    # plt.title("Orijinal Noktalar")
    # plt.imshow(high_res_image, cmap='gray')
    # plt.subplot(1, 2, 2)
    # plt.title("Kenarlar")
    # plt.imshow(edges, cmap='gray')
    # plt.show()

    return edge_coords
