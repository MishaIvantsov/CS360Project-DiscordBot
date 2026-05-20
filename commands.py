from __future__ import annotations

from database import delete_token
from calendar_api import (
    get_events_by_date,
    add_event,
    delete_event,
    edit_event,
    Event,
)
from auth import get_auth_url, get_credentials
from google.oauth2.credentials import Credentials as OAuth2Credentials


def get_creds_or_error(discord_id: str) -> tuple[OAuth2Credentials | None, str | None]:
    creds = get_credentials(discord_id)

    if creds is None:
        return (
            None,
            "⚠️ **Not linked.** Use `/link` to connect your Google Calendar first.",
        )

    return creds, None


async def link(discord_id: str) -> str:
    auth_url = get_auth_url(discord_id)

    return (
        "🔗 **Link your Google Calendar:**\n"
        "Click the link below and sign in with your Google account:\n"
        f"{auth_url}\n\n"
        "Once done, your calendar will be connected!"
    )


async def unlink(discord_id: str) -> str:
    success = delete_token(discord_id)

    if not success:
        return "⚠️ **Not linked.** You don't have a Google account connected."

    return "✅ **Unlinked!** Your Google account has been disconnected."


async def info(discord_id: str, date: str) -> str:
    creds, error = get_creds_or_error(discord_id)

    if error:
        return error

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


async def add(
    discord_id: str,
    title: str,
    day: int,
    month: int,
    year: int,
    time: str,
    location: str,
    description: str,
) -> str:
    creds, error = get_creds_or_error(discord_id)

    if error:
        return error

    time = time.upper().replace("AM", " AM").replace("PM", " PM")
    time = " ".join(time.split())

    new_event = Event(
        id="",
        title=title,
        day=day,
        month=month,
        year=year,
        time=time,
        location=location,
        description=description,
    )

    try:
        created = add_event(creds, new_event)

    except ValueError:
        return "⚠️ Time must include AM or PM. Example: `3:31 PM`"

    date_text = f"{month:02}/{day:02}/{year}"

    return (
        "✅ **Event Added!**\n"
        f"**[{created.id}] {title}**\n"
        f"🕐 {time}  |  📍 {location}\n"
        f"📅 {date_text}\n"
        f"_{description}_"
    )


async def edit(
    discord_id: str,
    event_id: str,
    field_to_edit: str,
    new_value: str,
) -> str:
    creds, error = get_creds_or_error(discord_id)

    if error:
        return error

    valid_fields = ["title", "day", "month", "year", "time", "location", "description"]

    if field_to_edit not in valid_fields:
        return f"⚠️ **Invalid field.** You can only edit: {', '.join(valid_fields)}"

    updated = edit_event(creds, event_id, **{field_to_edit: new_value})

    if updated is None:
        return f"⚠️ **Event Not Found.** No event with ID **{event_id}** exists."

    return (
        "✅ **Event Updated!**\n"
        f"Successfully changed `{field_to_edit}` to `{new_value}` for Event ID **{event_id}**."
    )


async def delete(discord_id: str, event_id: str) -> str:
    creds, error = get_creds_or_error(discord_id)

    if error:
        return error

    success = delete_event(creds, event_id)

    if not success:
        return f"⚠️ **Event Not Found.** No event with ID **{event_id}** exists."

    return f"✅ **Event Deleted!**\nSuccessfully deleted Event ID **{event_id}**."


async def help_cmd() -> str:
    return (
        "**Simon Bot Commands:**\n"
        "`/link` — link your Google Calendar\n"
        "`/unlink` — unlink your Google Calendar\n"
        "`/info` — list events on a date\n"
        "`/add` — add event\n"
        "`/edit` — edit an event\n"
        "`/delete` — delete an event"
    )
