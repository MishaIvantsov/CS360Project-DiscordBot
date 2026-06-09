from __future__ import annotations
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

import httplib2
import google_auth_httplib2
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials as OAuth2Credentials

load_dotenv()

logger = logging.getLogger(__name__)

CALENDAR_ID = "primary"
REQUEST_TIMEOUT = 10  # seconds; hard cap on each Google Calendar API call


@dataclass
class Event:
    id: str
    title: str
    date: str  # MM.DD.YYYY
    time: str  # HH:MM AM/PM
    location: str
    description: str
    attendees: list[str] | None = None


# --- Service Builder ---
def get_calendar_service(creds: OAuth2Credentials):
    """Build a Calendar service whose HTTP transport times out per request.

    Without a transport timeout, a stalled Google request blocks the worker
    thread forever, the awaiting coroutine never returns, and the bot looks
    stuck on "thinking". httplib2's timeout makes the call fail fast instead,
    raising an exception the callers below turn into a clean sentinel.
    """
    authed_http = google_auth_httplib2.AuthorizedHttp(
        creds, http=httplib2.Http(timeout=REQUEST_TIMEOUT)
    )
    return build("calendar", "v3", http=authed_http)


# --- Helpers ---
def _to_event(g_event: dict) -> Event:
    """Convert a Google Calendar API response dict to our Event dataclass."""
    start = g_event.get("start", {})
    dt_str = start.get("dateTime") or start.get("date", "")
    if "T" in dt_str:
        dt = datetime.fromisoformat(dt_str)
        date = dt.strftime("%m.%d.%Y")
        time = dt.strftime("%I:%M %p").lstrip("0")
    else:
        dt = datetime.strptime(dt_str, "%Y-%m-%d")
        date = dt.strftime("%m.%d.%Y")
        time = "All Day"

    raw_attendees = g_event.get("attendees", [])
    attendee_names = [a.get("displayName", a.get("email", "")) for a in raw_attendees]

    return Event(
        id=g_event.get("id", ""),
        title=g_event.get("summary", "No Title"),
        date=date,
        time=time,
        location=g_event.get("location", ""),
        description=g_event.get("description", ""),
        attendees=attendee_names,
    )


def _to_google_event(event: Event) -> dict:
    """Convert our Event dataclass to a Google Calendar API event dict."""
    dt = datetime.strptime(f"{event.date} {event.time}", "%m.%d.%Y %I:%M %p")
    dt_end = dt + timedelta(hours=1)

    g_attendees = []
    if event.attendees:
        for name in event.attendees:
            clean_name = name.replace("@", "").replace("<", "").replace(">", "")
            safe_email = f"{clean_name}@discord.local"
            g_attendees.append({"email": safe_email, "displayName": name})

    return {
        "summary": event.title,
        "location": event.location,
        "description": event.description,
        "start": {"dateTime": dt.isoformat(), "timeZone": "UTC"},
        "end": {"dateTime": dt_end.isoformat(), "timeZone": "UTC"},
        "attendees": g_attendees,
    }


# --- API Functions ---
async def get_events_by_date(creds: OAuth2Credentials, date: str) -> list[Event]:
    """Return all events on a given date (MM.DD.YYYY)."""
    service = get_calendar_service(creds)
    dt = datetime.strptime(date, "%m.%d.%Y")
    time_min = dt.replace(hour=0, minute=0, second=0).isoformat() + "Z"
    time_max = dt.replace(hour=23, minute=59, second=59).isoformat() + "Z"

    try:
        result = await asyncio.to_thread(
            lambda: service.events()
            .list(
                calendarId=CALENDAR_ID,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        return [_to_event(e) for e in result.get("items", [])]
    except Exception:
        logger.warning("get_events_by_date failed for %s", date, exc_info=True)
        return []


async def get_event_by_id(creds: OAuth2Credentials, event_id: str) -> Event | None:
    """Return a single event by its Google Calendar ID, or None if not found."""
    service = get_calendar_service(creds)
    try:
        g_event = await asyncio.to_thread(
            lambda: service.events()
            .get(calendarId=CALENDAR_ID, eventId=event_id)
            .execute()
        )
        return _to_event(g_event)
    except Exception:
        logger.warning("get_event_by_id failed for %s", event_id, exc_info=True)
        return None


async def add_event(creds: OAuth2Credentials, event: Event) -> Event | None:
    """Add a new event to the calendar. Returns the created event with its real ID."""
    service = get_calendar_service(creds)
    g_event = _to_google_event(event)
    try:
        created = await asyncio.to_thread(
            lambda: service.events()
            .insert(calendarId=CALENDAR_ID, body=g_event)
            .execute()
        )
        return _to_event(created)
    except Exception:
        logger.warning("add_event failed for %r", event.title, exc_info=True)
        return None


async def edit_event(
    creds: OAuth2Credentials, event_id: str, **kwargs
) -> Event | str | None:
    """Update fields on an existing event. Returns the updated event, a status string, or None."""
    service = get_calendar_service(creds)
    try:
        g_event = await asyncio.to_thread(
            lambda: service.events()
            .get(calendarId=CALENDAR_ID, eventId=event_id)
            .execute()
        )
    except Exception:
        logger.warning("edit_event lookup failed for %s", event_id, exc_info=True)
        return None

    if "add_attendee" in kwargs or "remove_attendee" in kwargs:
        current_attendees = g_event.get("attendees", [])
        current_names = [a.get("displayName", "") for a in current_attendees]

        if "add_attendee" in kwargs:
            person = kwargs["add_attendee"]
            if person in current_names:
                return "duplicate"
            clean_name = person.replace("@", "").replace("<", "").replace(">", "")
            safe_email = f"{clean_name}@discord.local"
            current_attendees.append({"email": safe_email, "displayName": person})

        elif "remove_attendee" in kwargs:
            person = kwargs["remove_attendee"]
            if person not in current_names:
                return "not_found"
            current_attendees = [
                a for a in current_attendees if a.get("displayName") != person
            ]
        g_event["attendees"] = current_attendees

    if "title" in kwargs:
        g_event["summary"] = kwargs["title"]
    if "location" in kwargs:
        g_event["location"] = kwargs["location"]
    if "description" in kwargs:
        g_event["description"] = kwargs["description"]

    if "date" in kwargs or "time" in kwargs:
        current = _to_event(g_event)
        new_date = kwargs.get("date", current.date)
        new_time = kwargs.get("time", current.time)
        dt = datetime.strptime(f"{new_date} {new_time}", "%m.%d.%Y %I:%M %p")
        dt_end = dt + timedelta(hours=1)
        g_event["start"] = {"dateTime": dt.isoformat(), "timeZone": "UTC"}
        g_event["end"] = {"dateTime": dt_end.isoformat(), "timeZone": "UTC"}

    try:
        updated = await asyncio.to_thread(
            lambda: service.events()
            .update(calendarId=CALENDAR_ID, eventId=event_id, body=g_event)
            .execute()
        )
        return _to_event(updated)
    except Exception:
        logger.warning("edit_event update failed for %s", event_id, exc_info=True)
        return None


async def delete_event(creds: OAuth2Credentials, event_id: str) -> bool:
    """Delete an event by ID. Returns True if deleted, False if not found."""
    service = get_calendar_service(creds)
    try:
        await asyncio.to_thread(
            lambda: service.events()
            .delete(calendarId=CALENDAR_ID, eventId=event_id)
            .execute()
        )
        return True
    except Exception:
        logger.warning("delete_event failed for %s", event_id, exc_info=True)
        return False
