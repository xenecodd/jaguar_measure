import sys
sys.path.append('/home/eypan/Downloads/fair_api_old/')
import Robot
import threading
import time


# Aynı süreç içindeki iş parçacıkları için threading.Lock kullanıyoruz.
mutex = threading.Lock()
robot = Robot.RPC("192.168.58.2")

# Hareket konfigürasyonları: her "lua" adı için ön (pre) ve varsa sonrası (post) hareket tanımlandı.
moves = {
    "small.lua": {
        "pre": ("MoveL", [-450, 130, 470, 82.80, 89.93, -7.30]),
        "post": ("MoveCart", [-375, 200, 580, -90, -90, 180])
    },
    "horizontal.lua": {
        "pre": ("MoveL", [-375, -120, 580, -90, -90, 180]),
        "post": ("MoveCart", [-425, -120, 510, -90, -90, 180])
    },
    "horizontal2.lua": {
        "pre": ("MoveL", [-425, 200, 510, -90, -90, 180]),
        "post": ("MoveCart", [-335, 250, 450, -90, 0, 90])
    },
    "vertical.lua": {
        "pre": ("MoveL", [-335, -400, 450, -90, 0, 90])
    }
}

vel_mul = 0.5

def send_move(move_type, coords, vel_mul):
    """Verilen hareket tipine göre robot hareket komutunu kilit altına alarak gönderir."""
    with mutex:
        if move_type == "MoveCart":
            robot.MoveCart(coords, 0, 0, vel=vel_mul * 54)
        elif move_type == "MoveL":
            robot.MoveL(coords, 0, 0, vel=vel_mul * 54)
        elif move_type == "MoveJ":
            robot.MoveJ(coords, 0, 0, vel=vel_mul * 100)
        else:
            raise ValueError(f"Unsupported move type: {move_type}")


# Robot hareketlerini sıralı olarak for döngüsü ile gönderelim.
for lua_name, move_config in moves.items():
    print(f"{lua_name} hareketine başlanıyor...")
    
    # Ön hareket
    if "pre" in move_config:
        move_type, coords = move_config["pre"]
        send_move(move_type, coords, vel_mul)
    
    # Hareketler arasında robotun komutu tamamlaması için kısa gecikme ekleyelim.
    time.sleep(1)
    
    # Eğer varsa post hareketi gönderelim.
    if "post" in move_config:
        move_type, coords = move_config["post"]
        send_move(move_type, coords, vel_mul)
    
    print(f"{lua_name} hareketi tamamlandı.\n")
    
    # Bir sonraki hareketten önce robotun komut işlemesi için bekleme süresi.
    time.sleep(2)
    