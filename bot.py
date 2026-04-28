import discord
import os
from dotenv import load_dotenv
load_dotenv()
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="?", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.command()
async def ping(ctx):
    await ctx.send("Hello!")
    
@bot.command()
async def say(ctx, *, mssg):
    await ctx.send(mssg)
    
@bot.command()
async def createevent(ctx, *, details: str):
    await ctx.send(f"Event created: {details} \nBy {ctx.author}")
    
@bot.command()
async def viewevents(ctx):
    await ctx.send(f"{ctx.author} Your current future events are: \n4/23/2026 Coffee")
     
bot.run(os.getenv("DISCORD_TOKEN")) 
