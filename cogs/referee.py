from discord import app_commands
from discord.ext import commands
from typing import Optional
from IRC.OsuSocket import OsuSocket

import discord

class referee(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.osu_socket = OsuSocket()

    @app_commands.command(name="create-lobby", description="Create a match")
    async def create_lobby(
        self,
        ctx           : discord.Interaction,
        make_command  : str,
        *,
        lobby_settings: Optional[str] = None,
        player_ping   : Optional[str] = None
    ):
        await self.osu_socket.privmsg("BanchoBot", make_command)