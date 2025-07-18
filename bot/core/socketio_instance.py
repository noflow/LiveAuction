from flask_socketio import SocketIO
from flask import session, request
from core.sheets import get_team_data_for_user

socketio = SocketIO(cors_allowed_origins="*")

@socketio.on("connect")
def on_connect():
    discord_id = session.get("discord_id")
    sid = request.sid

    if not discord_id:
        print("[Socket.IO] ❌ Connect blocked: no Discord ID in session.")
        return False  # deny connection

    team_data = get_team_data_for_user(discord_id)
    if not team_data:
        print(f"[Socket.IO] ⚠️ No team match for Discord ID {discord_id}")
        return

    team_data["isGMOrOwner"] = True
    socketio.emit("team:update", team_data, room=sid)
    print(f"[Socket.IO] ✅ Sent team:update to {discord_id} ({sid}) for team {team_data['teamName']}")
