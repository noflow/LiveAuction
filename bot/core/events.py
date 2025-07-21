from flask import session, request
from core.sheets import get_team_data_for_user
from .socketio_instance import socketio
from core.connections import connected_users

@socketio.on("connect")
def on_connect():
    print("🔌 WebSocket connected")
    print("📦 Session:", dict(session))

    discord_id = session.get("discord_id")
    sid = request.sid

    if not discord_id:
        print("[Socket.IO] ❌ Connect blocked: no Discord ID in session.")
        return False

    connected_users[str(discord_id)] = sid  # ✅ Store mapping

    team_data = get_team_data_for_user(discord_id)
    if not team_data:
        print(f"[Socket.IO] ⚠️ No team match for Discord ID {discord_id}")
        return

    team_data["isGMOrOwner"] = True
    socketio.emit("team:update", team_data, room=sid)
    print(f"[Socket.IO] ✅ Sent team:update to {discord_id} ({sid}) for {team_data['teamName']}")

@socketio.on("disconnect")
def on_disconnect():
    sid = request.sid
    to_remove = [uid for uid, val in connected_users.items() if val == sid]
    for uid in to_remove:
        del connected_users[uid]
        print(f"[Socket.IO] ❌ Removed {uid} from connected_users (SID: {sid})")


# core/connections.py
connected_users = {}