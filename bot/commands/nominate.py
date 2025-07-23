from discord import app_commands
import discord
import asyncio
from settings import get_setting
from core.sheets import get_team_limits
from core.auction_state import auction, auction_countdown
from commands.bidding import check_auto_bidders   # existing helper

@app_commands.command(name="nominate", description="Nominate a player for auction")
@app_commands.describe(player="Name of the player to nominate")
async def nominate(interaction: discord.Interaction, player: str):
    # Prevent overlapping nominations
    if auction.active_player:
        await interaction.response.send_message(
            "❌ A player is already up for bidding.", ephemeral=True
        )
        return

    # Basic roster & cap checks
    limits = get_team_limits(interaction.user.id)
    if not limits:
        await interaction.response.send_message(
            "❌ Could not locate your team data.", ephemeral=True
        )
        return

    if limits["roster_count"] >= get_setting("maxRosterSize"):
        await interaction.response.send_message(
            "🚫 Your roster is full. Cannot nominate.", ephemeral=True
        )
        return

    if limits["remaining"] < get_setting("nominationCost"):
        await interaction.response.send_message(
            "💰 Not enough cap space to nominate.", ephemeral=True
        )
        return

    # ─── Commit nomination ───
    opening_bid = get_setting("nominationCost")
    auction.active_player  = player
    auction.highest_bid    = opening_bid
    auction.highest_bidder = interaction.user
    auction.channel        = interaction.channel
    auction.nominator      = interaction.user

    # Announce & start timer
    await interaction.response.send_message(
        f"🎯 {interaction.user.display_name} nominated **{player}**! "
        f"Bidding starts at **${opening_bid}**. Timer running...",
        ephemeral=False
    )

    # Kick off timer
    if auction.timer_task:
        auction.timer_task.cancel()
    auction.start_timer()
    auction.timer_task = asyncio.create_task(auction_countdown())

    # Notify front‑end log via SocketIO (through bidding.py etc.)
    # Trigger auto‑bidders
    await check_auto_bidders()

# ────────────────── BACKEND HTTP HOOK ──────────────────
async def handle_nomination_from_backend(data):
    """Called by Flask route for /api/nominate"""
    from core.auction_state import auction, auction_countdown
    from settings import get_setting
    from commands.bidding import check_auto_bidders

    class DummyUser:
        def __init__(self, uid, username):
            self.id = uid
            self.display_name = username
            self.mention = f"<@{uid}>"

    user = DummyUser(data["userId"], data["username"])
    player = data["player"]

    if auction.paused:
        return {"status": "error", "message": "Draft is currently paused."}

    if auction.active_player:
        return {"status": "error", "message": "A player is already up for bidding."}

    if auction.nominator and auction.nominator.id != user.id:
        return {"status": "error", "message": "It's not your turn to nominate."}

    # Cap / roster checks
    limits = get_team_limits(user.id)
    if not limits:
        return {"status": "error", "message": "Could not locate your team data."}

    if limits["remaining"] < get_setting("nominationCost"):
        return {"status": "error", "message": "Not enough cap space to nominate."}

    if limits["roster_count"] >= get_setting("maxRosterSize"):
        return {"status": "error", "message": "Roster is already full."}

    # Nominate
    auction.active_player  = player
    auction.highest_bid    = get_setting("nominationCost")
    auction.highest_bidder = user
    auction.nominator      = user

    # Start timer
    if auction.timer_task:
        auction.timer_task.cancel()
    auction.start_timer()
    auction.timer_task = asyncio.create_task(auction_countdown())

    await check_auto_bidders()
    auction.advance_nomination_queue()

    return {
        "status": "success",
        "player": player,
        "message": f"✅ {player} nominated by {user.display_name}. "
                   f"Bidding starts at ${auction.highest_bid}"
    }

async def setup(bot):
    bot.tree.add_command(nominate)
