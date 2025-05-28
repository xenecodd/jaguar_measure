from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from config import Config

from sockets.robot_status_socket import register_socket_events
# Blueprint'leri düzgün import et
from routes.scan_routes import scan_bp
from routes.health_routes import health_bp
from routes.robot_routes import robot_bp

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
    register_socket_events(socketio)

    return app, socketio
