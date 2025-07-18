import discord 
from discord import app_commands
import time
from settings import get_setting
from core.auction_state import auction
from core.sheets import get_team_limits, get_team_roster
from core.socketio_instance import socketio
from commands.autobid_utils import check_auto_bidders  # ✅ avoids circular import

LOG_CHANNEL_ID = 999999999999999999  # Replace with real channel ID

@app_commands.command(name="minbid", description="Place the minimum bid on the active player")
async def minbid(interaction: discord.Interaction):
    user_limits = get_team_limits(interaction.user.id)

    if not user_limits:
        await interaction.response.send_message("❌ You are not listed as an Owner or GM.", ephemeral=True)
        return

    if user_limits['roster_count'] >= get_setting("max_roster_size"):
        await interaction.response.send_message("🚫 You’ve reached the max roster size.", ephemeral=True)
        return

    if user_limits['remaining'] < get_setting("minimum_bid_amount"):
        await interaction.response.send_message("💰 You don’t have enough cap space to place this bid.", ephemeral=True)
        return

    if not auction.active_player:
        await interaction.response.send_message("❌ No player is currently up for bidding.", ephemeral=True)
        return

    if interaction.user == auction.highest_bidder:
        await interaction.response.send_message("❌ You already have the highest bid.", ephemeral=True)
        return

    auction.highest_bid += 1
    auction.highest_bidder = interaction.user

    auction.bid_history.append({
        "player": auction.active_player,
        "amount": auction.highest_bid,
        "bidder": interaction.user.display_name,
        "timestamp": time.time()
    })

    team_info = get_team_limits(interaction.user.id)
    team_name = team_info["team"] if team_info else "Unknown Team"

    log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send(f"💰 **Team {team_name}** bid **${auction.highest_bid}** on **{auction.active_player}**")

    if time.time() > auction.ends_at - 10:
        auction.reset_timer()
        await auction.channel.send("🔁 Bid placed with <10s left — timer reset to 10 seconds!")

    await auction.channel.send(
        f"💰 {interaction.user.mention} has bid **${auction.highest_bid}** on **{auction.active_player}**!"
    )
    await interaction.response.send_message("✅ Your bid has been placed.", ephemeral=True)

    await emit_team_update(interaction.user.id)
    await check_auto_bidders()


@app_commands.command(name="flashbid", description="Place a custom amount bid")
@app_commands.describe(amount="Your custom bid amount")
async def flashbid(interaction: discord.Interaction, amount: int):
    user_limits = get_team_limits(interaction.user.id)

    if not user_limits:
        await interaction.response.send_message("❌ You are not listed as an Owner or GM.", ephemeral=True)
        return

    if user_limits['roster_count'] >= get_setting("max_roster_size"):
        await interaction.response.send_message("🚫 You’ve reached the max roster size.", ephemeral=True)
        return

    if user_limits['remaining'] < amount:
        await interaction.response.send_message("💰 You don’t have enough cap space to place this bid.", ephemeral=True)
        return

    if not auction.active_player:
        await interaction.response.send_message("❌ No player is currently up for bidding.", ephemeral=True)
        return

    if interaction.user == auction.highest_bidder:
        await interaction.response.send_message("❌ You already have the highest bid.", ephemeral=True)
        return

    if amount <= auction.highest_bid:
        await interaction.response.send_message("❌ Your bid must be higher than the current bid.", ephemeral=True)
        return

    auction.highest_bid = amount
    auction.highest_bidder = interaction.user

    auction.bid_history.append({
        "player": auction.active_player,
        "amount": auction.highest_bid,
        "bidder": interaction.user.display_name,
        "timestamp": time.time()
    })

    team_info = get_team_limits(interaction.user.id)
    team_name = team_info["team"] if team_info else "Unknown Team"

    log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send(f"💰 **Team {team_name}** bid **${auction.highest_bid}** on **{auction.active_player}**")

    if time.time() > auction.ends_at - 10:
        auction.reset_timer()
        await auction.channel.send("🔁 Flash bid placed with <10s left — timer reset to 10 seconds!")

    await auction.channel.send(
        f"⚡ {interaction.user.mention} flash bid **${amount}** on **{auction.active_player}**!"
    )
    await interaction.response.send_message("✅ Flash bid placed.", ephemeral=True)

    await emit_team_update(interaction.user.id)
    await check_auto_bidders()


@app_commands.command(name="autobid", description="Set an auto-bid for the current player")
@app_commands.describe(max_bid="Max amount you're willing to auto-bid")
async def autobid(interaction: discord.Interaction, max_bid: int):
    user_id = interaction.user.id
    auction.auto_bidders[user_id] = max_bid
    await interaction.response.send_message(f"✅ Auto-bid set up to **${max_bid}** for this player.", ephemeral=True)


async def emit_team_update(user_id):
    limits = get_team_limits(user_id)
    if not limits:
        return
    players = get_team_roster(limits["team"])
    socketio.emit("team:update", {
        "teamName": limits["team"],
        "salaryRemaining": limits["remaining"],
        "rosterCount": limits["roster_count"],
        "maxRoster": get_setting("max_roster_size"),
        "players": [{"name": p["name"], "cost": p["amount"]} for p in players],
        "isGMOrOwner": True
    })


async def setup(bot):
    bot.tree.add_command(minbid)
    bot.tree.add_command(flashbid)
    bot.tree.add_command(autobid)

