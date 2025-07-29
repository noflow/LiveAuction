
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

@app.before_request
def inject_discord_session():
    print("🔍 Headers received by Flask:", dict(request.headers))
    if "discord_id" not in session and "x-discord-id" in request.headers:
        session["discord_id"] = request.headers["x-discord-id"]
        session["discord_username"] = request.headers.get("x-discord-username", "unknown")
        print("🧩 Injected Discord session from headers")

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

    data = {
        "client_id": DISCORD_CLIENT_ID,
        "client_secret": DISCORD_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": DISCORD_REDIRECT_URI,
        "scope": "identify guilds"
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    r = requests.post("https://discord.com/api/oauth2/token", data=data, headers=headers)
    if r.status_code != 200:
        return f"Token request failed: {r.text}", 400

    token_json = r.json()
    access_token = token_json["access_token"]

    user_res = requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    if user_res.status_code != 200:
        return f"User fetch failed: {user_res.text}", 400

    user = user_res.json()
    session["discord_id"] = user["id"]
    session["username"] = f"{user['username']}#{user['discriminator']}"
    session["discord_username"] = user["username"]  # ✅ Required for /api/team

    return redirect("/draft/participate.html")

@app.route("/team")
def get_team():
    print("🔍 SESSION DATA:", dict(session))  # ✅ Debug full session
    username = session.get("discord_username") or request.headers.get("x-discord-username")
    if not username:
        return jsonify({"error": "Unauthorized"}), 401

    print("🔍 Resolving team for username:", username)

    try:
        team_data = get_team_data_for_user(username)
    except Exception as e:
        print(f"❌ Error fetching team data: {e}")
        return jsonify({"error": "Team lookup failed"}), 500

    if not team_data:
        return jsonify({"error": "Team not found"}), 404

    return jsonify(team_data)
