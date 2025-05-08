from flask import Flask
from flask_socketio import SocketIO
from config import Config
from backend import create_app

app, socketio = create_app()

if __name__ == '__main__':
    socketio.run(app, host=Config.HOST, port=Config.PORT,
                allow_unsafe_werkzeug=True,debug=False)