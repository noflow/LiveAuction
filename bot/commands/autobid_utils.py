
from core.auction_state import auction

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
