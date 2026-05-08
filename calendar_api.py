from __future__ import annotations
from dataclasses import dataclass


@dataclass
class Event:
    # FORMATTING
    id: str
    title: str
    date: str  # MM.DD.YYYY
    time: str  # HH:MM AM/PM
    location: str
    description: str


# DATA
EVENTS: list[Event] = [
    Event(
        id="001",
        title="Team Standup",
        date="04.28.2026",
        time="9:00 AM",
        location="Zoom",
        description="Daily team sync.",
    ),
    Event(
        id="002",
        title="Lunch with Sarah",
        date="04.28.2026",
        time="12:00 PM",
        location="Chipotle on Main St",
        description="Catching up.",
    ),
    Event(
        id="003",
        title="Sprint Planning",
        date="04.29.2026",
        time="10:00 AM",
        location="Conference Room B",
        description="Plan out tasks for the next two-week sprint.",
    ),
    Event(
        id="004",
        title="Project Demo 0.5",
        date="04.30.2026",
        time="11:00 AM",
        location="Zoom Meeting",
        description="Showing our bot :)",
    ),
    Event(
        id="005",
        title="Mom's Birthday Dinner",
        date="05.01.2026",
        time="7:00 PM",
        location="Olive Garden",
        description="Don't forget the card.",
    ),
]


# FAKE API Functions
def get_events_by_date(date: str) -> list[Event]:
    """Return all events matching the given date (MM.DD.YYYY)."""
    return [e for e in EVENTS if e.date == date]


def get_event_by_id(event_id: str) -> Event | None:
    """Return a single event by its ID, or None if not found."""
    return next((e for e in EVENTS if e.id == event_id), None)


def add_event(event: Event) -> Event:
    """Add a new event to the calendar."""
    EVENTS.append(event)
    return event


def edit_event(event_id: str, **kwargs) -> Event | None:
    """Update fields on an existing event by ID. Returns the updated event or None."""
    event = get_event_by_id(event_id)
    if event is None:
        return None
    for key, value in kwargs.items():
        if hasattr(event, key):
            setattr(event, key, value)
    return event


def delete_event(event_id: str) -> bool:
    """Delete an event by ID. Returns True if deleted, False if not found."""
    event = get_event_by_id(event_id)
    if event is None:
        return False
    EVENTS.remove(event)
    return True
