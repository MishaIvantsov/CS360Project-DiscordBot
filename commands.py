from __future__ import annotations
import discord
from calendar_api import (
    get_events_by_date,
    add_event,
    delete_event,
    edit_event,
    Event,
    EVENTS,
)

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from command_parser import ParsedCommand


# FINAL VERSION 0.5


async def handle(parsed: ParsedCommand, message: discord.Message) -> str:
    handlers = {
        "edit": edit,
        "add": add,
        "delete": delete,
        "info": info,
        "help": help_cmd,
    }

    handler = handlers.get(parsed.command)
    if handler is None:
        return f"Unknown command `{parsed.command}`. Try `@Simon/help`."

    return await handler(parsed.args, message)


async def edit(args: list[str], message: discord.Message) -> str:
    if len(args) < 3:
        return "⚠️ **Invalid format.** Please use: `@Simon/edit-<event_id>-<field>-<new_value>`"

    event_id = args[0]
    field_to_edit = args[1].lower()
    new_value = "-".join(args[2:])

    valid_fields = ["title", "date", "time", "location", "description"]
    if field_to_edit not in valid_fields:
        return f"⚠️ **Invalid field.** You can only edit: {', '.join(valid_fields)}"

    updated = edit_event(event_id, **{field_to_edit: new_value})

    if updated is None:
        return f"⚠️ **Event Not Found.** No event with ID **{event_id}** exists."

    return (
        f"✅ **Event Updated!**\n"
        f"Successfully changed `{field_to_edit}` to `{new_value}` for Event ID **{event_id}**."
    )


async def delete(args: list[str], message: discord.Message) -> str:
    if len(args) < 1:
        return "⚠️ **Missing Event.** Please use: `@Simon/delete-<event_id>`"

    event_id = args[0]
    success = delete_event(event_id)

    if not success:
        return f"⚠️ **Event Not Found.** No event with ID **{event_id}** exists."

    return f"✅ **Event Deleted!**\n" f"Successfully deleted Event ID **{event_id}**."


async def info(args: list[str], message: discord.Message) -> str:
    if len(args) < 1:
        return "⚠️ **Missing date.** Please use: `@Simon/info-<MM.DD.YYYY>`"

    date = args[0]

    events = get_events_by_date(date)

    if not events:
        return f"📅 No events found for **{date}**."

    lines = [f"📅 **Events on {date}:**\n"]
    for e in events:
        lines.append(
            f"**[{e.id}] {e.title}**\n"
            f"🕐 {e.time}  |  📍 {e.location}\n"
            f"_{e.description}_\n"
        )

    return "\n".join(lines)


async def add(args: list[str], message: discord.Message) -> str:
    # Expected format: @Simon/add-<title>-<date>-<time>-<location>-<description>
    if len(args) < 5:
        return (
            "⚠️ **Invalid format.** Please use:\n"
            "`@Simon/add-<title>-<MM.DD.YYYY>-<HH:MM AM/PM>-<location>-<description>`\n"
            "Example: `@Simon/add-Team Lunch-05.01.2026-12:00 PM-Chipotle-Team lunch!`"
        )

    title = args[0]
    date = args[1]
    time = args[2]
    location = args[3]
    description = "-".join(args[4:])  # allow hyphens in description

    new_id = str(len(EVENTS) + 1).zfill(3)

    new_event = Event(
        id=new_id,
        title=title,
        date=date,
        time=time,
        location=location,
        description=description,
    )

    add_event(new_event)

    return (
        f"✅ **Event Added!**\n"
        f"**[{new_id}] {title}**\n"
        f"🕐 {time}  |  📍 {location}\n"
        f"📅 {date}\n"
        f"_{description}_"
    )


async def help_cmd(args: list[str], message: discord.Message) -> str:
    return (
        "**Simon Bot Commands:**\n"
        "`@Simon/info-<MM.DD.YYYY>` — list events on a date\n"
        "`@Simon/add-<title>-<date>-<time>-<location>-<description>` — add event\n"
        "`@Simon/edit-<id>-<field>-<value>` — edit an event\n"
        "`@Simon/delete-<id>` — delete an event"
    )
