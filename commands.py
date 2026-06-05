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
    url = get_auth_url(discord_id)
    return (
        f"🔗 **Connect your Google Calendar** by clicking this link:\n<{url}>\n"
        f"*After authorizing, the bot will link automatically.*"
    )


async def unlink(args: list[str], message: discord.Message) -> str:
    discord_id = str(message.author.id)
    if delete_token(discord_id):
        return "✅ **Unlinked!** Your Google Calendar credentials have been removed from our system."
    return "⚠️ **Not linked.** You don't have an active calendar connection to remove."


async def info(args: list[str], message: discord.Message) -> str:
    if len(args) < 1:
        return "⚠️ **Missing date.** Please use: `@Simon/info-<date>` (MM.DD.YYYY)"

    creds, error = _get_creds_or_error(message)
    if error:
        return error
    assert creds is not None

    date_str = args[0]
    events = await get_events_by_date(creds, date_str)

    if not events:
        return f"📅 **No events found** for `{date_str}`."

    response = f"📅 **Events for {date_str}:**\n"
    for e in events:
        response += (
            f"**ID:** `{e.id}` | **{e.title}**\n"
            f"⏰ {e.time} | 📍 {e.location}\n"
            f"📝 {e.description}\n"
            f"👥 *Attendees:* {', '.join(e.attendees) if e.attendees else 'None'}\n\n"
        )
    return response.strip()


async def add(args: list[str], message: discord.Message) -> str:
    if len(args) < 5:
        return "⚠️ **Invalid format.** Use: `@Simon/add-<title>-<date>-<time>-<location>-<description>`"

    creds, error = _get_creds_or_error(message)
    if error:
        return error
    assert creds is not None

    new_event = Event(
        id="",
        title=args[0],
        date=args[1],
        time=args[2],
        location=args[3],
        description=args[4],
        attendees=[message.author.mention],  # Creator automatically added
    )

    created = await add_event(creds, new_event)
    if created is None:
        return "❌ **Error:** Failed to create event on Google Calendar."

    return f"✅ **Event Created!** ID is `{created.id}`."


async def edit(args: list[str], message: discord.Message) -> str:
    if len(args) < 3:
        return "⚠️ **Invalid format.** Please use: `@Simon/edit-<event_id>-<field>-<new_value>`"

    creds, error = _get_creds_or_error(message)
    if error:
        return error
    assert creds is not None

    event_id = args[0]
    field_to_edit = args[1].lower()

    # --- SCRUM 20: ATTENDEE LOGIC ---
    if field_to_edit == "attending_people":
        if len(args) < 4:
            return "⚠️ **Invalid format.** Use: `@Simon/edit-<event_id>-attending_people-<add/remove>-<name>`"

        action = args[2].lower()
        person = "-".join(args[3:])

        if person.lower() == "me":
            person = message.author.mention

        if action == "add":
            updated = await edit_event(creds, event_id, add_attendee=person)
            if updated == "duplicate":
                return f"⚠️ **{person}** is already on the attendee list."
        elif action == "remove":
            updated = await edit_event(creds, event_id, remove_attendee=person)
            if updated == "not_found":
                return f"⚠️ **{person}** was not found on the attendee list."
        else:
            return "⚠️ **Invalid action.** You must use `add` or `remove`."

        if not updated:
            return f"⚠️ **Event Not Found.** No event with ID **{event_id}** exists."

        attendee_list_str = (
            ", ".join(updated.attendees) if updated.attendees else "None"
        )
        return f"✅ **Attendee List Updated!**\nCurrent attendees for **{updated.title}**: {attendee_list_str}"

    # --- ORIGINAL FIELD LOGIC ---
    new_value = "-".join(args[2:])
    valid_fields = ["title", "date", "time", "location", "description"]
    if field_to_edit not in valid_fields:
        return f"⚠️ **Invalid field.** You can only edit: {', '.join(valid_fields)}, attending_people"

    updated = await edit_event(creds, event_id, **{field_to_edit: new_value})

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
    success = await delete_event(creds, event_id)

    if not success:
        return f"⚠️ **Event Not Found.** No event with ID **{event_id}** exists."

    return f"✅ **Event Deleted!**\nSuccessfully deleted Event ID **{event_id}**."


async def help_cmd(args: list[str], message: discord.Message) -> str:
    return (
        "**Simon Bot Commands:**\n"
        "`@Simon/link` — link your Google Calendar\n"
        "`@Simon/unlink` — unlink your calendar\n"
        "`@Simon/add-<title>-<date>-<time>-<location>-<description>` — add an event\n"
        "`@Simon/info-<date>` — view events for a date\n"
        "`@Simon/edit-<event_id>-<field>-<new_value>` — edit fields or `attending_people`"
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

    events = await get_events_by_date(creds, date)

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

    created = await add_event(creds, new_event)
    if created is None:
        return "❌ **Error:** Failed to create event on Google Calendar."

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

    updated = await edit_event(creds, event_id, **{field_to_edit: new_value})

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

    success = await delete_event(creds, event_id)

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
