from __future__ import annotations
from database import delete_token
import discord
from calendar_api import (
    get_events_by_date,
    add_event,
    delete_event,
    edit_event,
    Event,
)
from auth import get_auth_url, get_credentials
from google.oauth2.credentials import Credentials as OAuth2Credentials

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from command_parser import ParsedCommand


async def handle(parsed: ParsedCommand, message: discord.Message) -> str:
    handlers = {
        "edit": edit,
        "add": add,
        "delete": delete,
        "info": info,
        "help": help_cmd,
        "link": link,
        "unlink": unlink,
    }

    handler = handlers.get(parsed.command)
    if handler is None:
        return f"Unknown command `{parsed.command}`. Try `@Simon/help`."

    return await handler(parsed.args, message)


def _get_creds_or_error(
    message: discord.Message,
) -> tuple[OAuth2Credentials | None, str | None]:
    """Fetch credentials for the message author, or return an error string."""
    creds = get_credentials(str(message.author.id))
    if creds is None:
        return (
            None,
            "⚠️ **Not linked.** Use `@Simon/link` to connect your Google Calendar first.",
        )
    return creds, None


def _get_creds_or_error_by_discord_id(
    discord_id: str,
) -> tuple[OAuth2Credentials | None, str | None]:
    """Fetch credentials for a Discord user ID, or return an error string."""
    creds = get_credentials(discord_id)
    if creds is None:
        return (
            None,
            "⚠️ **Not linked.** Use `/link` to connect your Google Calendar first.",
        )
    return creds, None


async def link(args: list[str], message: discord.Message) -> str:
    discord_id = str(message.author.id)
    auth_url = get_auth_url(discord_id)
    return (
        f"🔗 **Link your Google Calendar:**\n"
        f"Click the link below and sign in with your Google account:\n"
        f"{auth_url}\n\n"
        f"Once done, your calendar will be connected!"
    )


async def unlink(args: list[str], message: discord.Message) -> str:

    discord_id = str(message.author.id)
    success = delete_token(discord_id)
    if not success:
        return "⚠️ **Not linked.** You don't have a Google account connected."
    return "✅ **Unlinked!** Your Google account has been disconnected."


async def info(args: list[str], message: discord.Message) -> str:
    if len(args) < 1:
        return "⚠️ **Missing date.** Please use: `@Simon/info-<MM.DD.YYYY>`"

    creds, error = _get_creds_or_error(message)
    if error:
        return error
    assert creds is not None

    date = args[0]
    events = get_events_by_date(creds, date)

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
    if len(args) < 5:
        return (
            "⚠️ **Invalid format.** Please use:\n"
            "`@Simon/add-<title>-<MM.DD.YYYY>-<HH:MM AM/PM>-<location>-<description>`\n"
            "Example: `@Simon/add-Team Lunch-05.01.2026-12:00 PM-Chipotle-Team lunch!`"
        )

    creds, error = _get_creds_or_error(message)
    if error:
        return error
    assert creds is not None

    title = args[0]
    date = args[1]
    time = args[2]
    location = args[3]
    description = "-".join(args[4:])

    new_event = Event(
        id="",
        title=title,
        date=date,
        time=time,
        location=location,
        description=description,
    )

    created = add_event(creds, new_event)

    return (
        f"✅ **Event Added!**\n"
        f"**[{created.id}] {title}**\n"
        f"🕐 {time}  |  📍 {location}\n"
        f"📅 {date}\n"
        f"_{description}_"
    )


async def edit(args: list[str], message: discord.Message) -> str:
    if len(args) < 3:
        return "⚠️ **Invalid format.** Please use: `@Simon/edit-<event_id>-<field>-<new_value>`"

    creds, error = _get_creds_or_error(message)
    if error:
        return error
    assert creds is not None

    event_id = args[0]
    field_to_edit = args[1].lower()
    new_value = "-".join(args[2:])

    valid_fields = ["title", "date", "time", "location", "description"]
    if field_to_edit not in valid_fields:
        return f"⚠️ **Invalid field.** You can only edit: {', '.join(valid_fields)}"

    updated = edit_event(creds, event_id, **{field_to_edit: new_value})

    if updated is None:
        return f"⚠️ **Event Not Found.** No event with ID **{event_id}** exists."

    return (
        f"✅ **Event Updated!**\n"
        f"Successfully changed `{field_to_edit}` to `{new_value}` for Event ID **{event_id}**."
    )


async def delete(args: list[str], message: discord.Message) -> str:
    if len(args) < 1:
        return "⚠️ **Missing Event.** Please use: `@Simon/delete-<event_id>`"

    creds, error = _get_creds_or_error(message)
    if error:
        return error
    assert creds is not None

    event_id = args[0]
    success = delete_event(creds, event_id)

    if not success:
        return f"⚠️ **Event Not Found.** No event with ID **{event_id}** exists."

    return f"✅ **Event Deleted!**\nSuccessfully deleted Event ID **{event_id}**."


async def help_cmd(args: list[str], message: discord.Message) -> str:
    return (
        "**Simon Bot Commands:**\n"
        "`@Simon/link` — link your Google Calendar\n"
        "`@Simon/unlink` — unlink your Google Calendar\n"
        "`@Simon/info-<MM.DD.YYYY>` — list events on a date\n"
        "`@Simon/add-<title>-<date>-<time>-<location>-<description>` — add event\n"
        "`@Simon/edit-<id>-<field>-<value>` — edit an event\n"
        "`@Simon/delete-<id>` — delete an event"
    )


async def link_slash(discord_id: str) -> str:
    auth_url = get_auth_url(discord_id)

    return (
        f"🔗 **Link your Google Calendar:**\n"
        f"Click the link below and sign in with your Google account:\n"
        f"{auth_url}\n\n"
        f"Once done, your calendar will be connected!"
    )


async def unlink_slash(discord_id: str) -> str:
    success = delete_token(discord_id)

    if not success:
        return "⚠️ **Not linked.** You don't have a Google account connected."

    return "✅ **Unlinked!** Your Google account has been disconnected."


async def info_slash(discord_id: str, date: str) -> str:
    creds, error = _get_creds_or_error_by_discord_id(discord_id)

    if error:
        return error

    assert creds is not None

    events = get_events_by_date(creds, date)

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


async def add_slash(
    discord_id: str,
    title: str,
    date: str,
    time: str,
    location: str,
    description: str,
) -> str:
    creds, error = _get_creds_or_error_by_discord_id(discord_id)

    if error:
        return error

    assert creds is not None

    new_event = Event(
        id="",
        title=title,
        date=date,
        time=time,
        location=location,
        description=description,
    )

    created = add_event(creds, new_event)

    return (
        f"✅ **Event Added!**\n"
        f"**[{created.id}] {title}**\n"
        f"🕐 {time}  |  📍 {location}\n"
        f"📅 {date}\n"
        f"_{description}_"
    )


async def edit_slash(
    discord_id: str,
    event_id: str,
    field_to_edit: str,
    new_value: str,
) -> str:
    creds, error = _get_creds_or_error_by_discord_id(discord_id)

    if error:
        return error

    assert creds is not None

    field_to_edit = field_to_edit.lower()

    valid_fields = ["title", "date", "time", "location", "description"]

    if field_to_edit not in valid_fields:
        return f"⚠️ **Invalid field.** You can only edit: {', '.join(valid_fields)}"

    updated = edit_event(creds, event_id, **{field_to_edit: new_value})

    if updated is None:
        return f"⚠️ **Event Not Found.** No event with ID **{event_id}** exists."

    return (
        f"✅ **Event Updated!**\n"
        f"Successfully changed `{field_to_edit}` to `{new_value}` for Event ID **{event_id}**."
    )


async def delete_slash(discord_id: str, event_id: str) -> str:
    creds, error = _get_creds_or_error_by_discord_id(discord_id)

    if error:
        return error

    assert creds is not None

    success = delete_event(creds, event_id)

    if not success:
        return f"⚠️ **Event Not Found.** No event with ID **{event_id}** exists."

    return f"✅ **Event Deleted!**\nSuccessfully deleted Event ID **{event_id}**."


async def help_slash() -> str:
    return (
        "**Simon Bot Commands:**\n"
        "`/link` — link your Google Calendar\n"
        "`/unlink` — unlink your Google Calendar\n"
        "`/info` — list events on a date\n"
        "`/add` — add event\n"
        "`/edit` — edit an event\n"
        "`/delete` — delete an event"
    )