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
    class DummyUser:
        def __init__(self, id, username):
            self.id = id
            self.display_name = username
            self.mention = f"<@{id}>"

    dummy_user = DummyUser(data["userId"], data["username"])
    result = await handle_nomination(dummy_user, None, data["player"])
    return result



async def setup(bot):
    bot.tree.add_command(nominate)
