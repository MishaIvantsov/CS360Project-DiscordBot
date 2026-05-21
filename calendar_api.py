from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from google.oauth2.credentials import Credentials as OAuth2Credentials
from googleapiclient.discovery import build

load_dotenv()

CALENDAR_ID = "primary"


@dataclass
class Event:
    id: str
    title: str
    date: str  # MM.DD.YYYY
    time: str  # HH:MM AM/PM
    location: str
    description: str
    attendees: list[str] = None


# --- Service Builder ---


def get_calendar_service(creds: OAuth2Credentials):
    """Build and return a Google Calendar service for a given user's credentials."""
    return build("calendar", "v3", credentials=creds)


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

    g_attendees = g_event.get("attendees", [])
    attendees_list = [
        a.get("displayName") or a.get("email", "") for a in g_attendees
    ]

    return Event(
        id=g_event.get("id", ""),
        title=g_event.get("summary", "No Title"),
        date=date,
        time=time,
        location=g_event.get("location", ""),
        description=g_event.get("description", ""),
        attendees=attendees_list,
    )


def _to_google_event(event: Event) -> dict:
    """Convert our Event dataclass to a Google Calendar API event dict."""
    dt = datetime.strptime(f"{event.date} {event.time}", "%m.%d.%Y %I:%M %p")
    dt_end = dt + timedelta(hours=1)

    return {
        "summary": event.title,
        "location": event.location,
        "description": event.description,
        "start": {"dateTime": dt.isoformat(), "timeZone": "UTC"},
        "end": {"dateTime": dt_end.isoformat(), "timeZone": "UTC"},
    }


# --- API Functions ---


def get_events_by_date(
    creds: OAuth2Credentials, date: str, end_date: str = None
) -> list[Event]:
    """Return all events on a given date (MM.DD.YYYY) or data range (MM.DD.YYYY:MM.DD.YYYY)."""
    service = get_calendar_service(creds)

    def parse_dt(d_str: str):
        for fmt in ("%m.%d.%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(d_str, fmt)
            except ValueError:
                continue
        raise ValueError(f"Unsupported format: {d_str}")

    start_dt = parse_dt(date).replace(tzinfo=timezone.utc)
    time_min = start_dt.isoformat()

    if end_date:
        end_dt = parse_dt(end_date).replace(tzinfo=timezone.utc) + timedelta(
            days=1
        )
    else:
        end_dt = start_dt + timedelta(days=1)
    time_max = end_dt.isoformat()

    result = (
        service.events()
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


def get_event_by_id(creds: OAuth2Credentials, event_id: str) -> Event | None:
    """Return a single event by its Google Calendar ID, or None if not found."""
    service = get_calendar_service(creds)
    try:
        g_event = service.events().get(calendarId=CALENDAR_ID, eventId=event_id).execute()
        return _to_event(g_event)
    except Exception:
        return None


def add_event(creds: OAuth2Credentials, event: Event) -> Event:
    """Add a new event to the calendar. Returns the created event with its real ID."""
    service = get_calendar_service(creds)
    g_event = _to_google_event(event)
    created = service.events().insert(calendarId=CALENDAR_ID, body=g_event).execute()
    return _to_event(created)


def edit_event(creds: OAuth2Credentials, event_id: str, **kwargs) -> Event | None:
    """Update fields on an existing event. Returns the updated event or None."""
    service = get_calendar_service(creds)
    try:
        g_event = service.events().get(calendarId=CALENDAR_ID, eventId=event_id).execute()
    except Exception:
        return None

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

    updated = (
        service.events()
        .update(calendarId=CALENDAR_ID, eventId=event_id, body=g_event)
        .execute()
    )
    return _to_event(updated)


def delete_event(creds: OAuth2Credentials, event_id: str) -> bool:
    """Delete an event by ID. Returns True if deleted, False if not found."""
    service = get_calendar_service(creds)
    try:
        service.events().delete(calendarId=CALENDAR_ID, eventId=event_id).execute()
        return True
    except Exception:
        return False
