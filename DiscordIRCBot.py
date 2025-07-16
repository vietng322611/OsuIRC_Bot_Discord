import Logger
from cogs.Referee import Referee

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
        await bot.add_cog(Referee(bot, configs["nick"], configs["pass"]))
        await bot.start(configs["token"])

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(e)
        raise e