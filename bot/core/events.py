from flask import session, request
from core.sheets import get_team_data_for_user
from .socketio_instance import socketio

@socketio.on("connect")
def on_connect():
    discord_id = session.get("discord_id")
    sid = request.sid

    if not discord_id:
        print("[Socket.IO] ❌ Connect blocked: no Discord ID in session.")
        return False

    team_data = get_team_data_for_user(discord_id)
    if not team_data:
        print(f"[Socket.IO] ⚠️ No team match for Discord ID {discord_id}")
        return

    team_data["isGMOrOwner"] = True
    socketio.emit("team:update", team_data, room=sid)
    print(f"[Socket.IO] ✅ Sent team:update to {discord_id} ({sid}) for {team_data['teamName']}")
