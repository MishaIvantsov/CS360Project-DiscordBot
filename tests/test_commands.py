import pytest
from unittest.mock import MagicMock, patch
import discord
from command_parser import ParsedCommand
from commands import handle


@pytest.fixture
def mock_message():
    return MagicMock(spec=discord.Message)


# handle() dispatch


@pytest.mark.asyncio
async def test_unknown_command(mock_message):
    parsed = ParsedCommand(name="Simon", command="fly", args=[])
    result = await handle(parsed, mock_message)
    assert "Unknown command" in result
    assert "`fly`" in result


# Testing help


@pytest.mark.asyncio
async def test_help_returns_all_commands(mock_message):
    parsed = ParsedCommand(name="Simon", command="help", args=[])
    result = await handle(parsed, mock_message)
    for cmd in ["info", "add", "edit", "delete"]:
        assert cmd in result


# Testing info()


@pytest.mark.asyncio
async def test_info_missing_date(mock_message):
    parsed = ParsedCommand(name="Simon", command="info", args=[])
    result = await handle(parsed, mock_message)
    assert "Missing date" in result


@pytest.mark.asyncio
async def test_info_no_events_found(mock_message):
    parsed = ParsedCommand(name="Simon", command="info", args=["01.01.2099"])
    with patch("commands.get_events_by_date", return_value=[]):
        result = await handle(parsed, mock_message)
    assert "No events found" in result
    assert "01.01.2099" in result


@pytest.mark.asyncio
async def test_info_returns_event_details(mock_message):
    fake_event = MagicMock()
    fake_event.id = "001"
    fake_event.title = "Team Lunch"
    fake_event.time = "12:00 PM"
    fake_event.location = "Chipotle"
    fake_event.description = "Lunch with the team"

    parsed = ParsedCommand(name="Simon", command="info", args=["05.01.2026"])
    with patch("commands.get_events_by_date", return_value=[fake_event]):
        result = await handle(parsed, mock_message)

    assert "Team Lunch" in result
    assert "12:00 PM" in result
    assert "Chipotle" in result


# Test add()


@pytest.mark.asyncio
async def test_add_missing_args(mock_message):
    parsed = ParsedCommand(name="Simon", command="add", args=["Title", "01.01.2026"])
    result = await handle(parsed, mock_message)
    assert "Invalid format" in result


@pytest.mark.asyncio
async def test_add_success(mock_message):
    args = ["Team Lunch", "05.01.2026", "12:00 PM", "Chipotle", "Team lunch!"]
    parsed = ParsedCommand(name="Simon", command="add", args=args)

    mock_created = MagicMock()
    mock_created.id = "abc123"

    with patch("commands.add_event", return_value=mock_created) as mock_add:
        result = await handle(parsed, mock_message)

    assert "Event Added" in result
    assert "Team Lunch" in result
    assert "Chipotle" in result
    mock_add.assert_called_once()


@pytest.mark.asyncio
async def test_add_description_with_hyphens(mock_message):
    args = ["Team Lunch", "05.01.2026", "12:00 PM", "Chipotle", "Bring", "your", "own"]
    parsed = ParsedCommand(name="Simon", command="add", args=args)

    mock_created = MagicMock()
    mock_created.id = "abc123"

    with patch("commands.add_event", return_value=mock_created) as mock_add:
        result = await handle(parsed, mock_message)

    assert "Event Added" in result
    mock_add.assert_called_once()
    event_arg = mock_add.call_args[0][0]
    assert event_arg.description == "Bring-your-own"


# Test delete()


@pytest.mark.asyncio
async def test_delete_missing_id(mock_message):
    parsed = ParsedCommand(name="Simon", command="delete", args=[])
    result = await handle(parsed, mock_message)
    assert "Missing Event" in result


@pytest.mark.asyncio
async def test_delete_event_not_found(mock_message):
    parsed = ParsedCommand(name="Simon", command="delete", args=["999"])
    with patch("commands.delete_event", return_value=False):
        result = await handle(parsed, mock_message)
    assert "Event Not Found" in result
    assert "999" in result


@pytest.mark.asyncio
async def test_delete_success(mock_message):
    parsed = ParsedCommand(name="Simon", command="delete", args=["001"])
    with patch("commands.delete_event", return_value=True):
        result = await handle(parsed, mock_message)
    assert "Event Deleted" in result
    assert "001" in result


# Test edit()


@pytest.mark.asyncio
async def test_edit_missing_args(mock_message):
    parsed = ParsedCommand(name="Simon", command="edit", args=["001", "title"])
    result = await handle(parsed, mock_message)
    assert "Invalid format" in result


@pytest.mark.asyncio
async def test_edit_invalid_field(mock_message):
    parsed = ParsedCommand(name="Simon", command="edit", args=["001", "color", "red"])
    result = await handle(parsed, mock_message)
    assert "Invalid field" in result


@pytest.mark.asyncio
async def test_edit_event_not_found(mock_message):
    parsed = ParsedCommand(
        name="Simon", command="edit", args=["999", "title", "New Title"]
    )
    with patch("commands.edit_event", return_value=None):
        result = await handle(parsed, mock_message)
    assert "Event Not Found" in result
    assert "999" in result


@pytest.mark.asyncio
async def test_edit_success(mock_message):
    parsed = ParsedCommand(
        name="Simon", command="edit", args=["001", "title", "New Title"]
    )
    with patch("commands.edit_event", return_value=MagicMock()):
        result = await handle(parsed, mock_message)
    assert "Event Updated" in result
    assert "title" in result
    assert "New Title" in result


@pytest.mark.asyncio
async def test_edit_value_with_hyphens(mock_message):
    # new_value should join args[2:] with "-"
    parsed = ParsedCommand(
        name="Simon", command="edit", args=["001", "description", "Part1", "Part2"]
    )
    with patch("commands.edit_event", return_value=MagicMock()) as mock_edit:
        await handle(parsed, mock_message)
    mock_edit.assert_called_once_with("001", description="Part1-Part2")


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["title", "date", "time", "location", "description"])
async def test_edit_all_valid_fields(field, mock_message):
    parsed = ParsedCommand(name="Simon", command="edit", args=["001", field, "value"])
    with patch("commands.edit_event", return_value=MagicMock()):
        result = await handle(parsed, mock_message)
    assert "Event Updated" in result
