from flask import session, request
from core.sheets import get_team_data_for_user_by_username
from .socketio_instance import socketio

@socketio.on("connect")
def on_connect():
    print("🔌 WebSocket connected")
    print("📦 Session:", dict(session))

    discord_username = session.get("username")  # <- changed from discord_id
    sid = request.sid

    if not discord_username:
        print("[Socket.IO] ❌ Connect blocked: no Discord username in session.")
        return False

    team_data = get_team_data_for_user(discord_username)
    if not team_data:
        print(f"[Socket.IO] ⚠️ No team match for username {discord_username}")
        return

    team_data["isGMOrOwner"] = True
    socketio.emit("team:update", team_data, room=sid)
    print(f"[Socket.IO] ✅ Sent team:update to {discord_username} ({sid}) for {team_data['teamName']}")


