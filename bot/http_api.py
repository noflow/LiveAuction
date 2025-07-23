from flask_session import Session  # ✅ NEW
from flask import Flask, request, jsonify, redirect, session
import asyncio, os, time, requests
from flask_cors import CORS
from commands.nominate import handle_nomination_from_backend
from core.socketio_instance import socketio
from core.sheets import get_team_data_for_user, get_team_role_id 


app = Flask(__name__)
app.secret_key = os.getenv("SESSION_SECRET", "defaultsecret")
app.config["SESSION_TYPE"] = "filesystem"  # ✅ REQUIRED for WebSocket session support
Session(app)                               # ✅ Attach Flask-Session
socketio.init_app(app, cors_allowed_origins="*")  # ✅ Must come after Session(app)
CORS(app)

DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI")

def start_flask_server():
    app.run(host="0.0.0.0", port=5050)

@app.route("/auth/discord")
def auth_discord():
    scope = "identify guilds"
    return redirect(
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={DISCORD_CLIENT_ID}"
        f"&redirect_uri={DISCORD_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope={scope}"
    )

@app.route("/auth/callback")
def auth_callback():
    code = request.args.get("code")
    if not code:
        return "Missing code", 400

    # Exchange code for token
    data = {
        "client_id": DISCORD_CLIENT_ID,
        "client_secret": DISCORD_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": DISCORD_REDIRECT_URI,
        "scope": "identify guilds"
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    r = requests.post("https://discord.com/api/oauth2/token", data=data, headers=headers)
    if r.status_code != 200:
        return f"Token request failed: {r.text}", 400

    token_json = r.json()
    access_token = token_json["access_token"]

    # Get user info
    user_res = requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    if user_res.status_code != 200:
        return f"User fetch failed: {user_res.text}", 400

    user = user_res.json()
    session["discord_id"] = user["id"]
    session["username"] = f"{user['username']}#{user['discriminator']}"

    return redirect("/draft/participate.html")


@app.route("/me", methods=["GET"])
def get_me():
    if "discord_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    return jsonify({
        "id": session["discord_id"],
        "username": session["username"]
    })

@app.route("/nominate", methods=["POST"])
def nominate():
    try:
        data = request.json
        asyncio.run(handle_nomination_from_backend(data))
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/force-nominate", methods=["POST"])
def force_nominate():
    from commands.nominate import force_nomination
    try:
        data = request.json
        asyncio.run(force_nomination(data))
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/skip-nominator", methods=["POST"])
def skip_nominator():
    from core.auction_state import auction
    try:
        auction.skip_nominator()
        return jsonify({"status": "skipped"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/toggle-pause", methods=["POST"])
def toggle_pause():
    from core.auction_state import auction
    try:
        auction.paused = not auction.paused
        return jsonify({"paused": auction.paused}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

import time
from flask import jsonify

@app.route("/auction/state", methods=["GET"])
def get_auction_state():
    try:
        from core.auction_state import auction
        from core.sheets import get_team_limits

        nominator = auction.nominator
        try:
            from core.sheets import get_team_limits
            team_info = get_team_limits(nominator.id) if nominator else None
            team_name = team_info["team"] if team_info else "Unknown"
        except Exception as sheet_error:
            print("[WARN] Sheet access failed:", sheet_error)
            team_name = "Unknown"

        return jsonify({
            "active": auction.active_player is not None,
            "player": auction.active_player,
            "high_bid": auction.highest_bid,
            "high_bidder": getattr(auction.highest_bidder, "display_name", "???") if auction.highest_bidder else None,
            "time_remaining": max(0, int(auction.ends_at - time.time())) if auction.ends_at else 0,
            "currentNominator": {
                "userId": getattr(nominator, "id", None),
                "teamId": getattr(nominator, "id", None),
                "displayName": getattr(nominator, "display_name", "???"),
                "team": team_name
            } if nominator else None
        })

    except Exception as e:
        import traceback
        print("[/auction/state ERROR]", traceback.format_exc())
        return jsonify({
            "error": "Something went wrong in /auction/state.",
            "message": str(e)
        }), 500


@app.route("/health", methods=["GET"])
def health():
    return "OK", 200




@app.route("/roles", methods=["GET"])
def get_roles():
    if "discord_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    from core.permissions import get_user_roles
    user_id = session["discord_id"]
    roles = get_user_roles(user_id)

    return jsonify(roles)

@app.route("/auction/history", methods=["GET"])
def get_bid_history():
    from core.auction_state import auction
    return jsonify(auction.bid_history[-50:])

@app.route("/api/admin/start-draft", methods=["POST"])
def start_draft_proxy():
    try:
        res = requests.post("http://bot.wcahockey.com/startdraft")  # 🔁 adjust URL if needed
        if res.status_code != 200:
            return jsonify({"error": "Bot did not respond properly"}), 500
        return jsonify({"status": "started"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def send_team_update(discord_id, sid):
    from .sheets import get_team_data_for_user

    team_data = get_team_data_for_user(discord_id)
    if not team_data:
        print(f"[team:update] No matching team for Discord ID {discord_id}")
        return

    team_data["isGMOrOwner"] = True
    socketio.emit("team:update", team_data, room=sid)
    print(f"[team:update] Sent to {discord_id} (SID: {sid}) → {team_data['teamName']}")


@app.route("/team", methods=["GET"])
def get_team_data():
    if "discord_id" not in session:
        return jsonify({ "error": "Not logged in" }), 401

    team_data = get_team_data_for_user(session["discord_id"])
    if not team_data:
        return jsonify({ "error": "No team found for user" }), 404

    team_data["isGMOrOwner"] = True
    team_data["username"] = session.get("username", "Unknown")
    team_data["role_id"] = get_team_role_id(team_data["teamName"])  # ⬅️ Add role ID

    return jsonify(team_data)


from core.sheets import load_draft_list

@app.route("/draft-list", methods=["GET"])
def get_draft_list():
    try:
        return jsonify(load_draft_list())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/debug")
def debug():
    return jsonify({"status": "✅ Flask is running", "version": "1.0"})
