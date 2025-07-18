from discord import app_commands
import discord
import time
from settings import get_setting
from core.sheets import get_team_limits
from core.auction_state import auction, auction_countdown
from commands.bidding import check_auto_bidders  # Import this function
import asyncio


@app_commands.command(name="nominate", description="Nominate a player for auction")
@app_commands.describe(player="Name of the player to nominate")
async def nominate(interaction: discord.Interaction, player: str):
    if auction.active_player:
        await interaction.response.send_message("❌ A player is already up for bidding.", ephemeral=True)
        return

    auction.active_player = player
    auction.highest_bidder = interaction.user
    auction.channel = interaction.channel
    auction.nominator = interaction.user

    # Set opening bid
    opening_bid = get_setting("minimum_bid_amount")
    auction.highest_bid = opening_bid
    auction.reset_timer()

    await interaction.response.send_message(
        f"🎯 {interaction.user.display_name} has nominated **{player}**! Bidding starts at **${opening_bid}**. Timer set to 10 seconds.\n{interaction.user.mention} is the current high bidder.",
        ephemeral=False
    )

    # Start countdown timer
    if auction.timer_task:
        auction.timer_task.cancel()
    auction.timer_task = asyncio.create_task(auction_countdown())

    # Trigger auto bidders
    await check_auto_bidders()

# At the bottom of bot/commands/nominate.py


async def handle_nomination_from_backend(data):
    from core.auction_state import auction, auction_countdown
    from core.sheets import get_team_limits
    from core.settings import get_setting
    from commands.bidding import check_auto_bidders

    class DummyUser:
        def __init__(self, id, username):
            self.id = id
            self.display_name = username
            self.mention = f"<@{id}>"

    user = DummyUser(data["userId"], data["username"])
    player = data["player"]

    if auction.paused:
        return { "status": "error", "message": "Draft is currently paused." }

    if auction.active_player:
        return { "status": "error", "message": "A player is already up for bidding." }

    if not auction.nominator or auction.nominator.id != user.id:
        return { "status": "error", "message": "It's not your turn to nominate." }

    limits = get_team_limits(user.id)
    if not limits:
        return { "status": "error", "message": "Could not locate your team data." }

    if limits["remaining"] < get_setting("nominationCost"):
        return { "status": "error", "message": "Not enough cap space to nominate." }

    if limits["roster_count"] >= get_setting("maxRosterSize"):
        return { "status": "error", "message": "Roster is already full." }

    # All checks passed — nominate
    auction.active_player = player
    auction.highest_bidder = user
    auction.nominator = user
    auction.highest_bid = get_setting("nominationCost")
    auction.reset_timer()

    if auction.timer_task:
        auction.timer_task.cancel()
    auction.timer_task = asyncio.create_task(auction_countdown())

    await check_auto_bidders()

    # Move nominator to end of queue
    auction.advance_nomination_queue()

    return {
        "status": "success",
        "player": player,
        "message": f"✅ {player} nominated by {user.display_name}. Bidding starts at ${auction.highest_bid}"
    }



async def setup(bot):
    bot.tree.add_command(nominate)

    remaining_spots = max(min_roster - limits["roster_count"], 0)
    min_required_cap = remaining_spots * min_bid

    if limits["remaining"] - get_setting("nomination_cost") < min_required_cap:
        await interaction.response.send_message(
            f"💰 You must reserve enough cap to fill at least {min_roster} players. "
            f"You need at least ${min_required_cap} remaining for {remaining_spots} roster spots.",
            ephemeral=True
        )
        return
    
