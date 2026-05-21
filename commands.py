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

import re
from datetime import datetime, timedelta

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
    if not args or (len(args) == 1 and args[0] == ""):
        return (
            "⚠️ **Missing criteria.** Please use: \n"
            "`@Simon/info-<MM.DD.YYYY>` \n"
            "'@Simon/info-today' \n"
            "'@Simon/info-this-week-Joe' \n"
            "'@Simon/info-07.01.2025:07.31.2025'"
        )

    creds, error = _get_creds_or_error(message)
    if error:
        return error
    assert creds is not None

    range_pattern = r"^(\d{4}-\d{2}-\d{2}):(\d{4}-\d{2}-\d{2})$"
    single_date_pattern = r"^\d{2}\.\d{2}\.\d{4}$"
    
    start_date = None
    end_date = None
    attendee_filter = None
    active_filters = []
    today_dt = datetime.now()

    for arg in args:
        range_match = re.match(range_pattern, arg)
        if range_match:
            start_date = range_match.group(1)
            end_date = range_match.group(2)
            active_filters.append(f"Range: '{arg}'")
            continue
        
        if re.match(single_date_pattern, arg):
            start_date = arg
            active_filters.append(f"Date: '{arg}'")
            continue

        if arg == "today":
            start_date = today_dt.strftime("%m.%d.%Y")
            active_filters.append("Today")
            continue
        elif arg == "tomorrow":
            tomorrow_dt = today_dt + timedelta(days=1)
            start_date = tomorrow_dt.strftime("%m.%d.%Y")
            active_filters.append("Tomorrow")
            continue
        elif arg == "this-week":
            start_date = today_dt.strftime("%m.%d.%Y")
            end_date = (today_dt + timedelta(days=7)).strftime("%m.%d.%Y")
            active_filters.append("This Week")
            continue

        if arg.lower() == "me":
            attendee_filter = message.author.name.lower()
            active_filters.append(f" Attendee: '{message.author.name}' (me)")
        else:
            attendee_filter = arg.lower()
            active_filters.append(f" Attendee: '{arg}'")

    try:
        fetch_date = start_date if start_date else today_dt.strftime("%m.%d.%Y")
        events = get_events_by_date(creds, fetch_date, end_date=end_date)                            
    except TypeError:
        events = get_events_by_date(creds, start_date or today_dt.strftime("%m.%d.%Y"))

    if not events:
        filter_summary = ", ".join(active_filters) if active_filters else "'None'"
        return f"📅 No events found for your criteria: {filter_summary}"

    if attendee_filter:
        filtered_events = []
        matched_attendee_names = set()

        for e in events:
            attendees_list = getattr(e, 'attendees', []) or []
            for attendee in attendees_list:
                attendees = str(attendee).lower()
                if attendee_filter in attendees:
                    filtered_events.append(e)
                    matched_attendee_names.add(str(attendee))
                    break

        if len(matched_attendee_names) > 1:
            names_found = ", ".join([f"'{n}'" for n in matched_attendee_names])
            await message.channel.send(
                f" Multiple matching attendees found: {names_found}. "
                "Displaying merged results."
            )

        events = filtered_events

        if not events:
            return f" **No events found** containing attendee: '{attendee_filter}' inside this date range."

    try:
        events.sort(key=lambda x: getattr(x, 'time', "") or getattr(x,'start_time', ''))
    except Exception:
        pass

    filter_header = " | ".join(active_filters) if active_filters else "Global Search"
    embed = discord.Embed(
        title="📅 Calendar Filter Output",
        description=f"**Active Filters:** {filter_header}\n**Total Matches:** `{len(events)}` event(s)",
        color=discord.Color.teal()
    )
    
    display_limit = 10
    truncated_events = events[:display_limit]

    for index, e in enumerate(truncated_events, start=1):
        location = getattr(e, 'location', 'No location specified') or 'No location specified'
        description = getattr(e, 'description', 'No details provided') or 'No details provided'
        event_time = getattr(e, 'time', 'Unknown Time')

        value_field = (
            f"🕒**Time:** {event_time}\n"
            f"📍 **Location:** {location}\n"
            f"📝 **Details:** {description}"
        )
        
        embed.add_field(
            name=f"{index}, {e.title} (ID: {e.id})",
            value = value_field,
            inline = False
        )

    if len(events) > display_limit:
        embed.set_footer(text=f"Showing 1-{display_limit} of {len(events)} items. Use pagination to view more.")

    await message.channel.send(embed=embed)

    return ""


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
