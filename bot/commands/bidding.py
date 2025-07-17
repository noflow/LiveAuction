import discord 
from discord import app_commands
import time
from settings import get_setting
from core.auction_state import auction
from core.sheets import get_team_limits

@app_commands.command(name="minbid", description="Place the minimum bid on the active player")
async def minbid(interaction: discord.Interaction):
    bid_amount = 1
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

    if time.time() > auction.ends_at - 10:
        auction.reset_timer()
        await auction.channel.send("🔁 Bid placed with <10s left — timer reset to 10 seconds!")

    await auction.channel.send(
        f"💰 {interaction.user.mention} has bid **${auction.highest_bid}** on **{auction.active_player}**!"
    )
    await interaction.response.send_message("✅ Your bid has been placed.", ephemeral=True)
    await check_auto_bidders()


@app_commands.command(name="flashbid", description="Place a custom amount bid")
@app_commands.describe(amount="Your custom bid amount")
async def flashbid(interaction: discord.Interaction, amount: int):
    bid_amount = amount
    user_limits = get_team_limits(interaction.user.id)

    if not user_limits:
        await interaction.response.send_message("❌ You are not listed as an Owner or GM.", ephemeral=True)
        return

    if user_limits['roster_count'] >= get_setting("max_roster_size"):
        await interaction.response.send_message("🚫 You’ve reached the max roster size.", ephemeral=True)
        return

    if user_limits['remaining'] < bid_amount:
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

    if time.time() > auction.ends_at - 10:
        auction.reset_timer()
        await auction.channel.send("🔁 Flash bid placed with <10s left — timer reset to 10 seconds!")

    await auction.channel.send(
        f"⚡ {interaction.user.mention} flash bid **${amount}** on **{auction.active_player}**!"
    )
    await interaction.response.send_message("✅ Flash bid placed.", ephemeral=True)
    await check_auto_bidders()


@app_commands.command(name="autobid", description="Set an auto-bid for the current player")
@app_commands.describe(max_bid="Max amount you're willing to auto-bid")
async def autobid(interaction: discord.Interaction, max_bid: int):
    user_id = interaction.user.id
    auction.auto_bidders[user_id] = max_bid
    await interaction.response.send_message(f"✅ Auto-bid set up to **${max_bid}** for this player.", ephemeral=True)


async def check_auto_bidders():
    for user_id, max_bid in auction.auto_bidders.items():
        if auction.highest_bid >= max_bid:
            continue
        if user_id == auction.highest_bidder.id:
            continue

        auction.highest_bid += 1
        auction.highest_bidder = auction.channel.guild.get_member(user_id)
        auction.reset_timer()
        await auction.channel.send(
            f"🤖 Auto-bid by <@{user_id}> to **${auction.highest_bid}**!"
        )
        break


# Register all commands in this file
async def setup(bot):
    bot.tree.add_command(minbid)
    bot.tree.add_command(flashbid)
    bot.tree.add_command(autobid)


async def handle_bid_from_backend(data):
    user_id = data["userId"]
    amount = data["amount"]

    # Dummy logic - replace with real auction state handling
    from core.auction_state import auction
    from core.permissions import get_team_limits
    from core.settings import get_setting

    user_limits = get_team_limits(user_id)
    if not user_limits:
        return {"status": "error", "message": "Unauthorized bidder"}

    if amount <= auction.highest_bid:
        return {"status": "error", "message": "Bid too low"}

    if user_limits["remaining"] < amount:
        return {"status": "error", "message": "Insufficient funds"}

    if user_limits["roster_count"] >= get_setting("maxRosterSize"):
        return {"status": "error", "message": "Roster full"}

    auction.highest_bid = amount
    auction.highest_bidder = user_id
    auction.reset_timer()

    return {
        "status": "success",
        "highBid": amount,
        "highBidder": user_id
    }
