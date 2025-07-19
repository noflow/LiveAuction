from flask import session, request
from core.sheets import get_team_data_for_user_by_username
from .socketio_instance import socketio

@socketio.on("connect")
def on_connect():
    username = session.get("username")
    sid = request.sid

    if not username:
        print("[Socket.IO] ❌ Connect blocked: no Discord ID in session.")
        return False

    team_data = get_team_data_for_user_by_username(username)
    if not team_data:
        print(f"[Socket.IO] ⚠️ No team match for username {username}")
        return

    team_data["isGMOrOwner"] = True
    socketio.emit("team:update", team_data, room=sid)
    print(f"[Socket.IO] ✅ Sent team:update to {username} ({sid}) for {team_data['teamName']}")

