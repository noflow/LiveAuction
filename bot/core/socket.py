
from flask_socketio import SocketIO
from http_api import app

socketio = SocketIO(app, cors_allowed_origins="*")
