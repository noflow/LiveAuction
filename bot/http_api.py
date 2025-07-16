from flask import Flask, request, jsonify
import asyncio
from commands.nominate import handle_nomination_from_backend
# from commands.bidding import handle_bid_from_backend  # example

app = Flask(__name__)

@app.route("/nominate", methods=["POST"])
def nominate():
    try:
        data = request.json
        asyncio.run(handle_nomination_from_backend(data))
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Future endpoint example:
# @app.route("/bid", methods=["POST"])
# def bid():
#     ...

def start_flask_server():
    app.run(host="0.0.0.0", port=5050)


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
