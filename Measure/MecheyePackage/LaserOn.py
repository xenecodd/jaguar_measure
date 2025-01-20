import time
from mecheye.shared import *
from mecheye.profiler import *
from mecheye.profiler_utils import *

profiler = Profiler()
status = profiler.connect("192.168.23.19", 5000)
if status.is_ok:
    print("bağlantı başarılı")
else:
    print("zort")
    
def activate_laser(duration: int = 5, cycles: int = 3) -> bool:
    """
    Lazeri belirli bir süre etkin tutar ve bu işlemi belirtilen döngü sayısı kadar tekrarlar.
    :param duration: Lazeri açık tutmak istediğiniz süre (saniye).
    :param cycles: Lazerin açılıp kapanacağı döngü sayısı.
    """
    for cycle in range(cycles):
        print(f"Döngü {cycle + 1}/{cycles}")

        # Lazer profil cihazını başlatmaya hazır duruma getir
        status = profiler.start_acquisition()
        if not status.is_ok():
            show_error(status)
            return False

        print("Lazer etkinleştirildi.")

        start_time = time.time()
        while time.time() - start_time < duration:
            # Lazer tetiklenir
            status = profiler.trigger_software()
            if not status.is_ok():
                show_error(status)
                return False
            time.sleep(5)  # Tetikleme işlemleri arasında kısa bir gecikme

        # Lazeri kapat
        status = profiler.stop_acquisition()
        if not status.is_ok():
            show_error(status)
            return False

        print("Lazer devreden çıkarıldı.")

        # Döngüler arasında kısa bir bekleme süresi
        if cycle < cycles - 1:
            print("Bir sonraki döngü için bekleniyor...")
            time.sleep(1)  # Döngüler arası gecikme süresi

    print("Tüm döngüler tamamlandı.")
    return True

# Lazeri 4 saniye boyunca açık tutacak ve bu işlemi 3 kez tekrar edecek
activate_laser(duration=1, cycles=5)