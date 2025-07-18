from discord import app_commands
from discord.ext import commands
from typing import Optional
from IRC.OsuSocket import OsuSocket

from IRC.IrcManager import ircManager

import discord
import logging
import asyncio
import tempfile

# idk i think this is important somehow
def to_name(thread_name: str) -> str:
    return thread_name.split("-")[1]

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
            self.logger.info(f"Fetching all active threads in channel: {channel.name}")
            for thread in channel.threads:
                name = thread.name
                if name.startswith("match-#mp_") or name.startswith("channel-#"):
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
                    self.logger.exception(f"Failed to unarchive thread {channel.name}, missing permissions")
                    return
                except discord.HTTPException as e:
                    self.logger.exception(f"Failed to unarchive thread {channel.name}: {e}")
                    return
            await self.osu_socket.privmsg(to_name(channel.name), message.content)
    
    async def cog_unload(self):
        if hasattr(self, "thread_update_task"):
            self.thread_update_task.cancel()

    async def update_threads(self):
        while True:
            for thread in self.threads.copy():
                # assume that archived threads are disbanded matches
                if thread.archived:
                    self.threads.remove(thread)
                    continue

                chat = ircManager.get_chat(to_name(thread.name))
                if chat:
                    messages = chat.get_staged_messages()
                    asyncio.create_task(self.send_messages_to_thread(thread, messages))
                else:
                    self.threads.remove(thread) # prevent concurrency issue
                    # avoid blocking when waiting to join a chat
                    asyncio.create_task(self.validate_thread(thread))
            await asyncio.sleep(0.5)

    async def validate_thread(self, thread: discord.Thread):
        channel = await self.osu_socket.join(to_name(thread.name))
        if channel:
            self.threads.add(thread)

    async def send_messages_to_thread(self, thread: discord.Thread, messages: list[str]):
        tasks = []
        for message in messages:
            tasks.append(thread.send(message))
        await asyncio.gather(*tasks, return_exceptions = True)

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
            self.logger.exception(e)
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
            f"match-#mp_{matches[0]}",
            f"Created match: https://osu.ppy.sh/mp/{matches[0]}"
        )
        if not thread: return
        
        if player_ping:
            await interaction.followup.send(player_ping)
        if lobby_settings:
            await self.osu_socket.privmsg(to_name(thread.name), lobby_settings)
            await thread.send(lobby_settings)
    
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
                self.logger.exception(e)
            finally:
                return
        else:
            if name.startswith("#mp_"):
                name = f"match-{name}"
            else:
                name = f"channel-{name}"
            await self.create_thread(
                interaction,
                name,
                f"Creating new thread for chat *{name}*"
            )

    @app_commands.command(name="export", description="Export chat log to a file (max 3000 messages)")
    async def export(
        self,
        interaction: discord.Interaction
    ):
        await interaction.response.defer()
        channel = interaction.channel
        if not isinstance(channel, discord.Thread):
            await interaction.followup.send("This command can only be used in a thread")
            return
        
        name = channel.name
        if not name.startswith("match-#mp_") and not name.startswith("channel-#"):
            await interaction.followup.send("This command can only be used in a match or channel thread")
            return
        
        name = to_name(name)
        try:
            with tempfile.NamedTemporaryFile(mode='w+', encoding='utf-8', suffix='.txt', delete=True) as temp_file:
                temp_file.write(f"Chat log for {name}\n")
                temp_file.write("--- Start of chat log ---\n")
                async for message in channel.history(limit=3000):
                    if message.author == self.bot.user:
                        temp_file.write(message.content + "\n")
                    else:
                        timestamp = message.created_at.strftime("%H:%M:%S")
                        temp_file.write(f"[{timestamp}] {message.author.name}: {message.content}\n")
                temp_file.write("--- End of chat log ---")
                temp_file.flush()
                temp_file.seek(0)
                await interaction.followup.send(file=discord.File(fp=temp_file.name, filename=f"{name}.txt"))
        except discord.Forbidden:
            self.logger.exception(f"Failed to read messages in thread {channel.name}, missing permissions")
            await interaction.followup.send("I don't have permissions to read messages in this thread")
        except discord.HTTPException as e:
            self.logger.exception(f"Failed to retrieve channel history: {e}")
            await interaction.followup.send("Failed to export chat log due to an error")
        except Exception as e:
            self.logger.exception(f"Unexpected error while exporting chat log: {e}")
            await interaction.followup.send("An unexpected error occurred while exporting the chat log")