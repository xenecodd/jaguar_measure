from types import SimpleNamespace
import os
config = SimpleNamespace(
    # Genel ayarlar
    pick=True,
    use_agg=False,
    put_back=False,
    drop_object = True,
    vel_mul=1.0,
    range_=2,
    file_path = os.path.join(os.path.dirname(__file__), "point_index.txt"),
    save_point_clouds=True,
    save_to_db=False,
    ignored_points = [4],
    same_object = False,
    same_place_index = None,
    # Tolerans ayarları: (hedef, tolerans)
    tolerances={
        "Feature1 (102.1)": (102.1, 2.0),
        "Feature2 (25mm/2)": (12.5, 0.5),
        "Feature3 (23.1)": (23.1, 1),
        "Feature4 (25mm/2)": (12.5, 0.5),
        "Feature5 (L40)": (40.0, 1),
        "Feature6 (L248)": (248.0, 2.0),
        "Feature7 (L42)": (42.0, 1.5),
        "Feature8 (L79.73)": (79.73, 1.5),
        "Feature9 (R1-50)": (50, 1.5),
        "Feature10 (R2-35)": (35, 1.5),
        "Feature11 (3mm)": (0, 3.0),
        "Feature12 (88.6)": (88.6, 1.5),
        "Feature13 (10.6)": (10.6, 1.0),
        "Feature14 (81.5)": (81.5, 1.5),
        "Feature15 (L23.4)": (23.4, 1.0),
        "Feature16 (L17.2)": (17.2, 1.0),
        "Feature17 (2C)": (0.0, 2.0)
    },
    
    # Robot pozisyonları
    robot_positions={
        "scrc": [-450, -130, 470, 82.80, 89.93, -7.30],
        "h_2": [-375, 100, 545, -90, -90, 180],
        "p_91": [-335, 100, 350, -90.00, -0.0005, 90.00],
        "notOK": [-621, 325, 511, 117, -83, -148]
    },

    # Veritabanı ayarları
    db_config={
        "host": "192.168.1.180",
        "user": "cobot_dbuser",
        "password": "um6vv$7*sJ@5Q*",
        "database": "cobot"
    }
)
