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
    events = get_events_by_date(creds, date_str)

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
        attendees=[message.author.mention]  # Creator automatically added
    )

    created = add_event(creds, new_event)
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
            updated = edit_event(creds, event_id, add_attendee=person)
            if updated == "duplicate":
                return f"⚠️ **{person}** is already on the attendee list."
        elif action == "remove":
            updated = edit_event(creds, event_id, remove_attendee=person)
            if updated == "not_found":
                return f"⚠️ **{person}** was not found on the attendee list."
        else:
            return "⚠️ **Invalid action.** You must use `add` or `remove`."
            
        if not updated:
            return f"⚠️ **Event Not Found.** No event with ID **{event_id}** exists."
            
        attendee_list_str = ", ".join(updated.attendees) if updated.attendees else "None"
        return f"✅ **Attendee List Updated!**\nCurrent attendees for **{updated.title}**: {attendee_list_str}"
    
    # --- ORIGINAL FIELD LOGIC ---
    new_value = "-".join(args[2:])
    valid_fields = ["title", "date", "time", "location", "description"]
    if field_to_edit not in valid_fields:
        return f"⚠️ **Invalid field.** You can only edit: {', '.join(valid_fields)}, attending_people"

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
        "`@Simon/unlink` — unlink your calendar\n"
        "`@Simon/add-<title>-<date>-<time>-<location>-<description>` — add an event\n"
        "`@Simon/info-<date>` — view events for a date\n"
        "`@Simon/edit-<event_id>-<field>-<new_value>` — edit fields or `attending_people`"
    )