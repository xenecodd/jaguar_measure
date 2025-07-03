import eventlet
eventlet.monkey_patch()

from config import Config
from __init__ import create_app

app, socketio = create_app()

if __name__ == '__main__':
    socketio.run(app, host=Config.HOST, port=Config.PORT)