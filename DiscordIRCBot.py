import discord
import os

from Logger import logger
from dotenv import load_dotenv
from discord.ext.commands.context import Context

load_dotenv()
TOKEN = os.getenv("TOKEN", "")

intents = discord.Intents.default()
intents.message_content = True
intents.presences = True
intents.members = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    logger.info(f'Logged in as {client.user}')

@client.event
async def on_message(ctx: Context):
    if ctx.author == client.user:
        return

    if ctx.message.content.startswith('$hello'):
        await ctx.channel.send('Hello!')

client.run(TOKEN, log_handler=None)