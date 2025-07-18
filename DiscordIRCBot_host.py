import Logger # static import for logger setup
from cogs.Referee import Referee
from keep_alive import keep_alive

from discord.ext import commands

import asyncio
import discord
import json
import logging

configs = json.load(open("configs.json", "r"))

intents = discord.Intents.default()
intents.message_content = True
intents.presences = True
intents.members = True

bot = commands.Bot(description="Osu!Irc bot", command_prefix=configs["prefix"], intents=intents)
logger = logging.getLogger()

@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user}')
    await bot.tree.sync()

async def main():
    async with bot:
        await bot.add_cog(Referee(bot, configs["nick"], configs["pass"], configs["irc_channel_id"]))
        await bot.start(configs["token"])

if __name__ == "__main__":
    keep_alive()  # Start the Flask server to keep the bot alive
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(e)
        raise e