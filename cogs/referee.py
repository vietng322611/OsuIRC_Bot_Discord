from discord import app_commands
from discord.ext import commands
from typing import Optional
from IRC.OsuSocket import OsuSocket

from IRC.IrcManager import ircManager

import discord
import logging
import asyncio

class Referee(commands.Cog):
    def __init__(self, bot: commands.Bot, nick: str, passw: str, channel_id: int) -> None:
        self.bot                          = bot
        self.creds                        = (nick, passw)
        self.channel_id                   = channel_id
        self.logger                       = logging.getLogger('discord')
        self.osu_socket                   = OsuSocket()
        self.threads: set[discord.Thread] = set()

    def get_thread_by_name(self, name: str) -> (discord.Thread | None):
        for thread in self.threads:
            if thread.name == name:
                return thread
        return None
            
    @commands.Cog.listener()
    async def on_ready(self):
        self.osu_socket.start(self.creds[0], self.creds[1])
        del self.creds
        channel = self.bot.get_channel(self.channel_id)
        if not isinstance(channel, discord.TextChannel):
            self.logger.debug(f"ID {self.channel_id} is not a text channel")
        else:
            self.logger.info(f"Fetching all active threads and 20 recent archived threads in channel: {channel.name}")
            # Fetch active threads in cache
            self.threads.update(channel.threads)
            # Fetch 20 recent archived threads
            async for thread in channel.archived_threads(limit=20):
                self.threads.add(thread)
            self.logger.info(f"Found {len(self.threads)} threads")
        self.thread_update_task = asyncio.create_task(self.update_threads())

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author == self.bot.user: return
        channel = message.channel
        if not isinstance(channel, discord.Thread): return
        if channel in self.threads:
            if channel.archived:
                try:
                    self.threads.remove(channel)
                    channel = await channel.edit(archived=False)
                    self.threads.add(channel)   
                except discord.Forbidden:
                    self.logger.error(f"Failed to unarchive thread {channel.name}, missing permissions")
                    return
                except discord.HTTPException as e:
                    self.logger.error(f"Failed to unarchive thread {channel.name}: {e}")
                    return
            await self.osu_socket.privmsg(channel.name, message.content)
    
    async def cog_unload(self):
        if hasattr(self, "thread_update_task"):
            self.thread_update_task.cancel()

    async def update_threads(self):
        while True:
            for thread in self.threads.copy():
                chat = ircManager.get_chat(thread.name)
                if chat:
                    messages = chat.get_staged_messages()
                    asyncio.create_task(self.send_messages_to_thread(thread, messages))
                else:
                    # avoid blocking when waiting to join a chat
                    asyncio.create_task(self.validate_thread(thread))
            await asyncio.sleep(0.5)
        
    async def validate_thread(self, thread: discord.Thread):
        channel = await self.osu_socket.join(thread.name)
        if not channel:
            self.threads.remove(thread)

    async def send_messages_to_thread(self, thread: discord.Thread, messages: list[str]):
        tasks = []
        for message in messages:
            tasks.append(thread.send(message))
        await asyncio.gather(*tasks, return_exceptions = True)
    
    async def send_to_thread_and_match(self, thread: discord.Thread, message: str):
        await self.osu_socket.privmsg(thread.name, message)
        await thread.send(message)

    async def create_thread(
        self,
        interaction: discord.Interaction,
        name: str,
        message: str
    ) -> (discord.Thread | None):
        try:
            await interaction.followup.send(message)
            original_response = await interaction.original_response()
            thread = await original_response.create_thread(name=name, auto_archive_duration=60)
            self.threads.add(thread)
            return thread
        except Exception as e:
            self.logger.error(e)
            match e:
                case discord.Forbidden:
                    await interaction.followup.send("I don't have permissions to create a thread")
                case discord.HTTPException:
                    await interaction.followup.send("Failed to create new thread")
                case ValueError:
                    await interaction.followup.send("This message does not have guild info attached")

    @app_commands.command(name="create-lobby", description="Create new lobby for tournament match")
    async def create_lobby(
        self,
        interaction   : discord.Interaction,
        make_command  : str,
        *,
        lobby_settings: Optional[str] = None,
        player_ping   : Optional[str] = None
    ):
        await interaction.response.defer()
        await self.osu_socket.privmsg("BanchoBot", make_command)
        matches = await ircManager.listen_for_pattern(
                "BanchoBot",
                "https://osu.ppy.sh/mp/(\\d+)"
            )
        if len(matches) < 1:
            await interaction.followup.send("Failed to create a tournament match")
            return
        
        thread = await self.create_thread(
            interaction,
            f"#mp_{matches[0]}",
            f"Created match: https://osu.ppy.sh/mp/{matches[0]}"
        )
        if not thread: return
        
        if player_ping:
            await interaction.followup.send(player_ping)
        if lobby_settings:
            await self.send_to_thread_and_match(thread, lobby_settings)
    
    @app_commands.command(name="join", description="Join an existing chat")
    async def join(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer()
        if self.get_thread_by_name(name):
            await interaction.followup.send(f"Already joined chat *{name}*")
            return

        if not await self.osu_socket.join(name):
            try:
                await interaction.followup.send(f"Failed to join chat *{name}*")
            except Exception as e:
                self.logger.error(e)
            finally:
                return
        else:
            await self.create_thread(
                interaction,
                name,
                f"Creating new thread for chat *{name}*"
            )

    @app_commands.command(name="export", description="Export chat log to a file")
    async def export(
        self,
        interaction: discord.Interaction,
        *,
        name: Optional[str] = None
    ):
        raise NotImplementedError