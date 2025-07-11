import os
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
INTENTS = discord.Intents.default()
INTENTS.members = True
INTENTS.guilds = True
INTENTS.message_content = True

class DraftBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=INTENTS)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        print(f"✅ Slash commands synced to guild {GUILD_ID}")

bot = DraftBot()

# Example: /nominate
@bot.tree.command(name="nominate", description="Nominate a player for auction")
@app_commands.describe(player="Name of the player to nominate")
async def nominate(interaction: discord.Interaction, player: str):
    await interaction.response.send_message(
        f"🎯 {interaction.user.display_name} has nominated **{player}** for bidding!",
        ephemeral=False
    )
    # You’ll later trigger the countdown + web update here.

@bot.event
async def on_ready():
    print(f"🤖 Bot ready: {bot.user}")

bot.run(TOKEN)
