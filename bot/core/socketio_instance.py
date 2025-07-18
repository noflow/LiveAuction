from flask_socketio import SocketIO

socketio = SocketIO(cors_allowed_origins="*")

# Ensure event handlers are registered
import core.events
