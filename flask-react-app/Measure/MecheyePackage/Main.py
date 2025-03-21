import os
import subprocess
import multiprocessing
import threading
import time
from mecheye_trigger import robot, TriggerWithExternalDeviceAndFixedRate
from mecheye.profiler import Profiler

# Global değişkenler
scan_process = None  
profiler = Profiler()

def run_scan(stop_event):
    """scan.py dosyasını başlatan fonksiyon"""
    global scan_process
    scan_process = subprocess.Popen(["python3", "/home/eypan/Documents/JaguarInterface/flask-react-app/Measure/MecheyePackage/scan.py"])
    
    # Stop sinyali bekle
    while not stop_event.is_set():
        time.sleep(0.1)  # Bekleme süresi

    # Stop sinyali geldi, alt süreci kapat
    if scan_process:
        scan_process.terminate()

def monitor_robot(stop_event, restart_event):
    """Robot durumunu kontrol eder, gerekiyorsa scan process'ini kapatır"""
    global scan_process
    while True:
        if robot.GetDI(8, 0) == (0, 0):
            # print("robot.GetDI(8,0) == (0,0)")
            pass
        else:
            print("robot.GetDI(8,0) is not (0,0) - scan.py kapatılıyor...")
            profiler.stop_acquisition()
            profiler.disconnect()
            robot.StopMotion()


            stop_event.set()  # Alt process için stop sinyalini gönder
            print("Stop sinyali gönderildi, alt process duracak!")
            break  # Döngüyü kır

        time.sleep(1)  # 1 saniye bekle

    # Kullanıcıya tekrar başlatmak isteyip istemediğini sor
    start = time.time()
    while True:
        if robot.GetDI(9, 0) == (0, 1):
            restart_event.set()  # Yeniden başlatma sinyalini gönder
            break
        elif time.time() - start>3:
                print("Baslat butonuna basarak yeniden baslayabilirsiniz")
                start = time.time()

if __name__ == "__main__":
    while True:
        if robot.GetDI(9, 0) == (0, 1):
            stop_event = multiprocessing.Event()  # Alt process'i durdurmak için
            restart_event = multiprocessing.Event()  # Yeniden başlatma için

            # Scan işlemini başlatan process
            p = multiprocessing.Process(target=run_scan, args=(stop_event,))
            p.start()

            # Robot kontrolünü başlatan thread
            monitor_thread = threading.Thread(target=monitor_robot, args=(stop_event, restart_event), daemon=True)
            monitor_thread.start()

            # Ana process'i çalışır halde tut (alt process kapansa bile)
            while True:
                time.sleep(0.2)

                # Kullanıcı tekrar başlatmak istemezse çık
                if restart_event.is_set():
                    break
        time.sleep(0.1)