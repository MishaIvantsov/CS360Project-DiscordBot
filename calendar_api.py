from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials as OAuth2Credentials

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
    attendees: list[str] | None = None  # NEW: Added for Scrum 20

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

    # Extract attendees from Google's format
    raw_attendees = g_event.get("attendees", [])
    attendee_names = [a.get("displayName", a.get("email", "")) for a in raw_attendees]

    return Event(
        id=g_event.get("id", ""),
        title=g_event.get("summary", "No Title"),
        date=date,
        time=time,
        location=g_event.get("location", ""),
        description=g_event.get("description", ""),
        attendees=attendee_names,  # NEW
    )


def _to_google_event(event: Event) -> dict:
    """Convert our Event dataclass to a Google Calendar API request dict."""
    dt = datetime.strptime(f"{event.date} {event.time}", "%m.%d.%Y %I:%M %p")
    dt_end = dt + timedelta(hours=1)

    # Format attendees for Google API
    g_attendees = []
    if event.attendees:
        for name in event.attendees:
            safe_email = f"{name.replace('@', '').replace('<', '').replace('>', '')}@discord.local"
            g_attendees.append({"email": safe_email, "displayName": name})

    return {
        "summary": event.title,
        "location": event.location,
        "description": event.description,
        "start": {"dateTime": dt.isoformat(), "timeZone": "UTC"},
        "end": {"dateTime": dt_end.isoformat(), "timeZone": "UTC"},
        "attendees": g_attendees,  # NEW
    }


# --- API Functions ---


def get_events_by_date(creds: OAuth2Credentials, date_str: str) -> list[Event]:
    """Return all events for a given date (MM.DD.YYYY) from the user's calendar."""
    service = get_calendar_service(creds)
    dt = datetime.strptime(date_str, "%m.%d.%Y")

    time_min = dt.replace(hour=0, minute=0, second=0).isoformat() + "Z"
    time_max = dt.replace(hour=23, minute=59, second=59).isoformat() + "Z"

    try:
        events_result = (
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
    except Exception:
        return []

    g_events = events_result.get("items", [])
    return [_to_event(e) for e in g_events]

def get_event_by_id(creds: OAuth2Credentials, event_id: str) -> Event | None:
    """Retrieves a specific calendar event by its ID."""
    try:
        service = get_calendar_service(creds)
        event = service.events().get(calendarId="primary", eventId=event_id).execute()
        return _to_event(event)
    except Exception:
        return None


def add_event(creds: OAuth2Credentials, event: Event) -> Event | None:
    """Add a new event to the user's Google Calendar. Returns the created event."""
    service = get_calendar_service(creds)
    body = _to_google_event(event)

    try:
        created = service.events().insert(calendarId=CALENDAR_ID, body=body).execute()
        return _to_event(created)
    except Exception:
        return None


def edit_event(creds: OAuth2Credentials, event_id: str, **kwargs) -> Event | None:
    """Update fields on an existing event. Returns the updated event or None."""
    service = get_calendar_service(creds)
    try:
        g_event = (
            service.events().get(calendarId=CALENDAR_ID, eventId=event_id).execute()
        )
    except Exception:
        return None

    # Handle Scrum 20 Attending People operations
    if "add_attendee" in kwargs or "remove_attendee" in kwargs:
        current_attendees = g_event.get("attendees", [])
        current_names = [a.get("displayName", "") for a in current_attendees]

        if "add_attendee" in kwargs:
            person = kwargs["add_attendee"]
            if person in current_names:
                return "duplicate"
            safe_email = f"{person.replace('@', '').replace('<', '').replace('>', '')}@discord.local"
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

    updated = (
        service.events()
        .update(calendarId=CALENDAR_ID, eventId=event_id, body=g_event)
        .execute()
    )
    return _to_event(updated)


def delete_event(creds: OAuth2Credentials, event_id: str) -> bool:
    """Delete an event by ID. Returns True if successful, False otherwise."""
    service = get_calendar_service(creds)
    try:
        service.events().delete(calendarId=CALENDAR_ID, eventId=event_id).execute()
        return True
    except Exception:
        return False
