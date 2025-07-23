import time
import asyncio
from settings import get_setting
from core.sheets import (
    update_team_after_win,
    append_player_to_team_tab,
    remove_player_from_draft
)
from core.socketio_instance import socketio

class AuctionState:
    """In‑memory state for the running auction."""
    def __init__(self):
        self.active_player = None          # str | None
        self.highest_bid = 0               # int
        self.highest_bidder = None         # discord.Member | DummyUser
        self.ends_at = None                # unix ts, when clock expires
        self.timer_task = None             # asyncio.Task
        self.channel = None                # discord.TextChannel
        self.nominator = None              # discord.Member
        self.auto_bidders = {}             # {user_id: max_bid}
        self.draft_started = False

        self.nomination_queue = []
        self.nomination_index = 0
        self.bid_history = []
        self.paused = False

    # ────────────────── TIMER HELPERS ──────────────────
    def start_timer(self):
        """Start the main_clock countdown & broadcast timer:start."""
        main_clock = get_setting("main_clock") or 30
        self.ends_at = time.time() + main_clock
        socketio.emit("timer:start", {"duration": main_clock, "max": main_clock})
        # also push first tick so UI lines up
        socketio.emit("timer:tick", {"seconds": main_clock})

    def reset_timer(self):
        """Reset to the shorter reset_clock & broadcast timer:reset."""
        reset_clock = get_setting("reset_clock") or 10
        self.ends_at = time.time() + reset_clock
        socketio.emit("timer:reset", {"seconds": reset_clock})

    # ────────────────── QUEUE HELPERS ──────────────────
    def advance_nomination_queue(self):
        if not self.nomination_queue:
            return None
        self.nomination_index = (self.nomination_index + 1) % len(self.nomination_queue)
        return self.nomination_queue[self.nomination_index]

    def reset(self):
        """Clear state between draft sessions."""
        self.__init__()

# Global singleton
auction = AuctionState()

# ────────────────── BACKGROUND COUNTDOWN ──────────────────
async def auction_countdown():
    """Runs in background; ticks clock & finalizes player on expiry."""
    while True:
        remaining = int(auction.ends_at - time.time()) if auction.ends_at else 0
        if remaining <= 0:
            break
        socketio.emit("timer:tick", {"seconds": remaining})
        await asyncio.sleep(1)

    socketio.emit("timer:end")

    if auction.highest_bidder:
        await auction.channel.send(
            f"⏱️ Time's up! **{auction.active_player}** is won by "
            f"**{auction.highest_bidder.display_name}** for **${auction.highest_bid}**!"
        )
        # Google Sheet updates
        team_name = update_team_after_win(auction.highest_bidder.id, auction.highest_bid)
        if team_name:
            append_player_to_team_tab(team_name, auction.active_player, auction.highest_bid)
            remove_player_from_draft(auction.active_player)
            await auction.channel.send(
                f"📥 **{auction.active_player}** added to **{team_name}** roster."
            )
    else:
        await auction.channel.send(
            f"⏱️ Time's up! No bids were placed for **{auction.active_player}**."
        )

    # Clear player‑specific state
    auction.active_player = None
    auction.highest_bid = 0
    auction.highest_bidder = None
    auction.ends_at = None
    auction.timer_task = None
    auction.channel = None
    auction.nominator = None
    auction.auto_bidders.clear()
