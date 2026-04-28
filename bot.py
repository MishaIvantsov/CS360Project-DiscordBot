import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

from command_parser import parse

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=commands.when_mentioned_or("?"), intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

async def main():
    token = os.getenv("DISCORD_TOKEN")
    if token is None:
        raise RuntimeError("DISCORD_TOKEN is not set in .env")

    async with bot:
        await bot.load_extension("cogs.calendar_cog")
        await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())