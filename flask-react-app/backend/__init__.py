# __init__.py
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from config import Config

# Blueprint'leri import et
from routes.scan_routes import scan_bp
from routes.health_routes import health_bp
from routes.robot_routes import robot_bp

# Robot servisini import et
from services.robot_service import start_robot_service, set_status_callback

import atexit
from apscheduler.schedulers.background import BackgroundScheduler


MAX_LOG_LINES = 1000       # Maksimum tutulacak satır sayısı

def trim_log_file():
    try:
        with open(Config.LOG_FILE, 'r') as f:
            lines = f.readlines()
        if len(lines) > MAX_LOG_LINES:
            with open(Config.LOG_FILE, 'w') as f:
                f.writelines(lines[-MAX_LOG_LINES:])
            print(f"[LOG] Log dosyası budandı ({len(lines)} satır → {MAX_LOG_LINES})")
    except Exception as e:
        print(f"[ERROR] Log budama hatası: {e}")

# Scheduler başlat
scheduler = BackgroundScheduler()
scheduler.add_job(func=trim_log_file, trigger="interval", minutes=5)
scheduler.start()

# Uygulama kapanırken scheduler’ı durdur
atexit.register(lambda: scheduler.shutdown())

# SocketIO objesi global
socketio = SocketIO(cors_allowed_origins="*", async_mode='threading', 
                    ping_interval=Config.SOCKET_PING_INTERVAL,
                    ping_timeout=Config.SOCKET_PING_TIMEOUT,
                    max_http_buffer_size=1024 * 1024)

def create_app():
    app = Flask(__name__)
    CORS(app)

    # Blueprint'leri kaydet
    app.register_blueprint(scan_bp)
    app.register_blueprint(robot_bp)
    app.register_blueprint(health_bp)
    
    # SocketIO'yu init et
    socketio.init_app(app)
    
    # Robot servisi için callback fonksiyonunu ayarla
    def emit_robot_data(event_name, data):
        """Robot verilerini SocketIO ile yayınla"""
        socketio.emit(event_name, data)
    
    # Callback'i robot servisine kaydet
    set_status_callback(emit_robot_data)
    
    # Robot servisini başlat (bağımsız thread'lerde)
    start_robot_service()

    return app, socketio