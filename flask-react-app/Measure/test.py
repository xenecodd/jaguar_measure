from concurrent.futures import thread
import threading
import pandas as pd
import time
import os
import sys
sys.path.append('/home/eypan/Downloads/fair_api_old/'),
import Robot
robot = Robot.RPC("192.168.58.2")

tcp_cords = []
start_time = time.time()

def save_tcp_cords_periodically(interval=1, filename="tcp_cords.xlsx"):
    while True:
        if tcp_cords:
            try:
                # Yeni verileri kopyala ve temizle
                temp = tcp_cords.copy()
                tcp_cords.clear()
                df_new = pd.DataFrame(temp, columns=["TCP", "Time"])
                if os.path.exists(filename):
                    # Var olan dosyayı oku, üzerine ekle
                    df_existing = pd.read_excel(filename)
                    df_combined = pd.concat([df_existing, df_new], ignore_index=True)
                else:
                    df_combined = df_new
                df_combined.to_excel(filename, index=False)
                print(f"{len(temp)} yeni kayıt eklendi: {filename}")
            except Exception as e:
                print(f"Excel yazma hatası: {e}")
        time.sleep(interval)

def update_tcp():
    while True:
        tcp = robot.GetActualTCPPose()[1][:3]
        tcp_cords.append([tcp, time.time() - start_time])
        time.sleep(0.01)




save_thread = threading.Thread(target=save_tcp_cords_periodically, daemon=False)
save_thread.start()
        
tcp_update_thread = threading.Thread(target=update_tcp, daemon=False)
tcp_update_thread.start()