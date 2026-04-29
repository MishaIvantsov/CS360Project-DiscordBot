from __future__ import annotations
import discord
from command_parser import ParsedCommand
 
 
async def handle(parsed: ParsedCommand, message: discord.Message) -> str:
    handlers = {
        "edit":   edit,
        "add":    add,
        "delete": delete,
    }
 
    handler = handlers.get(parsed.command)
    if handler is None:
        return f"Unknown command `{parsed.command}`. Try `@Simon/help`."
 
    return await handler(parsed.args, message)
 
 
async def edit(args: list[str], message: discord.Message) -> str:
    # Aiden's work goes here
    ...
 
 
async def add(args: list[str], message: discord.Message) -> str:
    # Sesen's work goes here
    ...
 
 
async def delete(args: list[str], message: discord.Message) -> str:
    # Johnny's work goes here
    ...
 