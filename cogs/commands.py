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
    # Validate argument length
    if len(args) < 3:
        return "⚠️ **Invalid format.** Please use: `@Simon/edit-<event_id>-<field>-<new_value>`"

    event_id = args[0]
    field_to_edit = args[1].lower()

    # Join the remaining arguments back together in case the new value contains hyphens.
    new_value = "-".join(args[2:])

    # Prevent users from trying to edit the 'id' or non-existent attributes
    valid_fields = ["title", "date", "time", "location", "description"]
    if field_to_edit not in valid_fields:
        return f"⚠️ **Invalid field.** You can only edit: {', '.join(valid_fields)}"

    # FOR v0.5 DEMO: We removed the calendar_api call to mock the response 
    # without crashing the bot! It just immediately returns success.

    return (
        f"✅ **Event Updated!**\n"
        f"Successfully changed `{field_to_edit}` to `{new_value}` for Event ID **{event_id}**.\n"
        f"> *Mocking Google Calendar sync and attendee notifications for v0.5.*"
    )
    ...
 
 
async def add(args: list[str], message: discord.Message) -> str:
    # Sesen's work goes here
    ...
 
 
async def delete(args: list[str], message: discord.Message) -> str:
    # Johnny's work goes here
    ...
 
