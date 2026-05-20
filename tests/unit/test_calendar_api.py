from __future__ import annotations
from unittest.mock import MagicMock, patch
import pytest  # noqa: F401
from google.oauth2.credentials import Credentials as OAuth2Credentials

# Patch Google auth and build before calendar_api loads
with (
    patch(
        "google.oauth2.service_account.Credentials.from_service_account_file",
        return_value=MagicMock(),
    ),
    patch("googleapiclient.discovery.build", return_value=MagicMock()),
):
    from calendar_api import (
        _to_event,
        _to_google_event,
        Event,
        get_events_by_date,
        get_event_by_id,
        add_event,
        edit_event,
        delete_event,
    )


# --- Sample Data ---

SAMPLE_G_EVENT = {
    "id": "abc123",
    "summary": "Team Lunch",
    "start": {"dateTime": "2026-05-01T12:00:00+00:00"},
    "location": "Chipotle",
    "description": "Lunch with the team",
}

SAMPLE_ALL_DAY_G_EVENT = {
    "id": "def456",
    "summary": "Holiday",
    "start": {"date": "2026-05-01"},
    "location": "",
    "description": "",
}

SAMPLE_EVENT = Event(
    id="abc123",
    title="Team Lunch",
    date="05.01.2026",
    time="12:00 PM",
    location="Chipotle",
    description="Lunch with the team",
)


def make_mock_creds() -> OAuth2Credentials:
    """Return a mock OAuth2Credentials object."""
    return MagicMock(spec=OAuth2Credentials)


# --- _to_event() ---


def test_to_event_maps_fields_correctly():
    event = _to_event(SAMPLE_G_EVENT)
    assert event.id == "abc123"
    assert event.title == "Team Lunch"
    assert event.date == "05.01.2026"
    assert event.time == "12:00 PM"
    assert event.location == "Chipotle"
    assert event.description == "Lunch with the team"


def test_to_event_all_day():
    event = _to_event(SAMPLE_ALL_DAY_G_EVENT)
    assert event.date == "05.01.2026"
    assert event.time == "All Day"


def test_to_event_missing_summary():
    g_event = {
        "id": "abc123",
        "start": {"dateTime": "2026-05-01T12:00:00+00:00"},
    }
    event = _to_event(g_event)
    assert event.title == "No Title"


def test_to_event_missing_optional_fields():
    g_event = {
        "id": "abc123",
        "start": {"dateTime": "2026-05-01T12:00:00+00:00"},
    }
    event = _to_event(g_event)
    assert event.location == ""
    assert event.description == ""


# --- _to_google_event() ---


def test_to_google_event_maps_fields_correctly():
    g_event = _to_google_event(SAMPLE_EVENT)
    assert g_event["summary"] == "Team Lunch"
    assert g_event["location"] == "Chipotle"
    assert g_event["description"] == "Lunch with the team"


def test_to_google_event_has_start_and_end():
    g_event = _to_google_event(SAMPLE_EVENT)
    assert "start" in g_event
    assert "end" in g_event
    assert "dateTime" in g_event["start"]
    assert "dateTime" in g_event["end"]


def test_to_google_event_end_is_one_hour_after_start():
    from datetime import datetime

    g_event = _to_google_event(SAMPLE_EVENT)
    start = datetime.fromisoformat(g_event["start"]["dateTime"])
    end = datetime.fromisoformat(g_event["end"]["dateTime"])
    assert (end - start).seconds == 3600


# --- get_events_by_date() ---


def test_get_events_by_date_returns_events():
    mock_service = MagicMock()
    mock_service.events().list().execute.return_value = {"items": [SAMPLE_G_EVENT]}

    with patch("calendar_api.get_calendar_service", return_value=mock_service):
        result = get_events_by_date(make_mock_creds(), "05.01.2026")

    assert len(result) == 1
    assert result[0].title == "Team Lunch"


def test_get_events_by_date_returns_empty_list():
    mock_service = MagicMock()
    mock_service.events().list().execute.return_value = {"items": []}

    with patch("calendar_api.get_calendar_service", return_value=mock_service):
        result = get_events_by_date(make_mock_creds(), "01.01.2099")

    assert result == []


# --- get_event_by_id() ---


def test_get_event_by_id_returns_event():
    mock_service = MagicMock()
    mock_service.events().get().execute.return_value = SAMPLE_G_EVENT

    with patch("calendar_api.get_calendar_service", return_value=mock_service):
        result = get_event_by_id(make_mock_creds(), "abc123")

    assert result is not None
    assert result.id == "abc123"
    assert result.title == "Team Lunch"


def test_get_event_by_id_returns_none_when_not_found():
    mock_service = MagicMock()
    mock_service.events().get().execute.side_effect = Exception("Not found")

    with patch("calendar_api.get_calendar_service", return_value=mock_service):
        result = get_event_by_id(make_mock_creds(), "nonexistent")

    assert result is None


# --- add_event() ---


def test_add_event_returns_created_event():
    mock_service = MagicMock()
    mock_service.events().insert().execute.return_value = SAMPLE_G_EVENT

    with patch("calendar_api.get_calendar_service", return_value=mock_service):
        result = add_event(make_mock_creds(), SAMPLE_EVENT)

    assert result.id == "abc123"
    assert result.title == "Team Lunch"


def test_add_event_calls_insert():
    mock_service = MagicMock()
    mock_service.events().insert().execute.return_value = SAMPLE_G_EVENT

    with patch("calendar_api.get_calendar_service", return_value=mock_service):
        add_event(make_mock_creds(), SAMPLE_EVENT)

    mock_service.events().insert.assert_called()


# --- edit_event() ---


def test_edit_event_updates_title():
    updated_g_event = {**SAMPLE_G_EVENT, "summary": "Updated Lunch"}
    mock_service = MagicMock()
    mock_service.events().get().execute.return_value = dict(SAMPLE_G_EVENT)
    mock_service.events().update().execute.return_value = updated_g_event

    with patch("calendar_api.get_calendar_service", return_value=mock_service):
        result = edit_event(make_mock_creds(), "abc123", title="Updated Lunch")

    assert result is not None
    assert result.title == "Updated Lunch"


def test_edit_event_returns_none_when_not_found():
    mock_service = MagicMock()
    mock_service.events().get().execute.side_effect = Exception("Not found")

    with patch("calendar_api.get_calendar_service", return_value=mock_service):
        result = edit_event(make_mock_creds(), "nonexistent", title="Whatever")

    assert result is None


# --- delete_event() ---


def test_delete_event_returns_true_on_success():
    mock_service = MagicMock()

    with patch("calendar_api.get_calendar_service", return_value=mock_service):
        result = delete_event(make_mock_creds(), "abc123")

    assert result is True


def test_delete_event_returns_false_when_not_found():
    mock_service = MagicMock()
    mock_service.events().delete().execute.side_effect = Exception("Not found")

    with patch("calendar_api.get_calendar_service", return_value=mock_service):
        result = delete_event(make_mock_creds(), "nonexistent")

    assert result is False

import pytest
from calendar_api import add_attendee, remove_attendee, _to_event, _to_google_event

def test_add_attendee_success():
    """Test successfully adding a new attendee to an event."""
    event = {"summary": "Scrum Meeting", "attendees": []}
    updated_event = add_attendee(event, "test_user@uw.edu")
    assert "test_user@uw.edu" in updated_event["attendees"]

def test_add_attendee_duplicate():
    """Test that duplicate attendees are handled gracefully and not added twice."""
    event = {"summary": "Scrum Meeting", "attendees": ["test_user@uw.edu"]}
    updated_event = add_attendee(event, "test_user@uw.edu")
    assert updated_event["attendees"].count("test_user@uw.edu") == 1

def test_remove_attendee_success():
    """Test successfully removing an attendee from an event."""
    event = {"summary": "Scrum Meeting", "attendees": ["test_user@uw.edu"]}
    updated_event = remove_attendee(event, "test_user@uw.edu")
    assert "test_user@uw.edu" not in updated_event["attendees"]

def test_remove_attendee_not_found():
    """Test removing an attendee who isn't on the list doesn't crash."""
    event = {"summary": "Scrum Meeting", "attendees": ["test_user@uw.edu"]}
    updated_event = remove_attendee(event, "missing_user@uw.edu")
    assert "test_user@uw.edu" in updated_event["attendees"]
    assert len(updated_event["attendees"]) == 1

def test_attendee_round_trip_conversion():
    """Test that attendee lists map correctly between internal and Google event formats."""
    # Mock a raw Google API event structure
    google_event = {
        "id": "123",
        "summary": "Project Sync",
        "start": {"dateTime": "2026-05-20T10:00:00Z"},
        "end": {"dateTime": "2026-05-20T11:00:00Z"},
        "attendees": [{"email": "aiden@uw.edu"}, {"email": "misha@uw.edu"}]
    }
    
    # Convert Google -> Internal
    internal_event = _to_event(google_event)
    assert "aiden@uw.edu" in internal_event.attendees
    assert "misha@uw.edu" in internal_event.attendees
    
    # Convert Internal -> Google
    back_to_google = _to_google_event(internal_event)
    assert any(a["email"] == "aiden@uw.edu" for a["email"] in back_to_google["attendees"])
