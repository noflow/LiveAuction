from flask import Flask, request, jsonify
import asyncio
from commands.nominate import handle_nomination_from_backend

app = Flask(__name__)

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

@app.route("/auction/state", methods=["GET"])
def get_auction_state():
    from core.auction_state import auction
    from core.sheets import get_team_limits
    import time

    nominator = auction.nominator
    team_info = get_team_limits(nominator.id) if nominator else None
    team_name = team_info["team"] if team_info else "Unknown"

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

def start_flask_server():
    app.run(host="0.0.0.0", port=5050)

