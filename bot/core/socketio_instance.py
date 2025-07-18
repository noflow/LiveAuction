from flask_socketio import SocketIO

socketio = SocketIO(cors_allowed_origins="*", manage_session=False)


# Ensure event handlers are registered
import core.events
