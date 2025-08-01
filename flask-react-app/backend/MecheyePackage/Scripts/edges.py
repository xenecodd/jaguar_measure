import numpy as np
import cv2
import matplotlib.pyplot as plt
from scipy.spatial import cKDTree

def get_scale():
    return 13

def upscale_points(points, scale, image_size=(300, 300)):
    upscale_size = (image_size[0] * scale, image_size[1] * scale)
    image = np.zeros(upscale_size, dtype=np.uint8)
    for x, y in points:
        x, y = int(x * scale), int(y * scale)
        if 0 <= x < upscale_size[1] and 0 <= y < upscale_size[0]:
            cv2.circle(image, (x, y), radius=0, color=255, thickness=3)
    return image

def detect_edges(image):
    blurred = cv2.GaussianBlur(image, (1,1), 0.5)
    edges = cv2.Canny(image, 150, 200)
    return edges

def radius_outlier_removal(points, radius=5, min_neighbors=3):
    tree = cKDTree(points)
    counts = tree.query_ball_point(points, r=radius)
    mask = np.array([len(c) >= min_neighbors for c in counts])
    return points[mask]

def process_and_visualize(points):
    scale = get_scale()
    high_res_image = upscale_points(points, scale=scale)
    edges = detect_edges(high_res_image)

    edge_coords = np.column_stack(np.where(edges > 0))
    # Radius-based outlier temizliği
    edge_coords = radius_outlier_removal(edge_coords, radius=5, min_neighbors=3)

    return edge_coords
