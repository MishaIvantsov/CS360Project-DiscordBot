import os
import re
import discord
from dotenv import load_dotenv
import command_parser
 
#LAUNCH THIS FOR DEMO 0.5

load_dotenv()
 
intents = discord.Intents.default()
intents.message_content = True
 
client = discord.Client(intents=intents)
 
 
@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
 
 
@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    if client.user not in message.mentions:
        return
 
    text = re.sub(r"<@!?\d+>", "@Simon", message.content).strip()
 
    response = await command_parser.parse(text, message)
    await message.reply(response)
 
 
client.run(os.getenv("DISCORD_TOKEN"))