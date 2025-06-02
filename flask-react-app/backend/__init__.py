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