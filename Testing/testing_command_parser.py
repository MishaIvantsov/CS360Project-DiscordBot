import pytest
import discord
from unittest.mock import AsyncMock, MagicMock, patch
from command_parser import parse, ParsedCommand

@pytest.fixture
def mock_message():
    return MagicMock(spec=discord.Message)


@pytest.fixture
def mock_handle():
    with patch("commands.handle", new_callable=AsyncMock) as m:
        m.return_value = ""
        yield m


# Invalid-input tests

@pytest.mark.asyncio
async def test_no_at_symbol(mock_message):
    result = await parse("Simon/help", mock_message)
    assert result == "I didn't understand that. Try `@Simon/help`."

@pytest.mark.asyncio
async def test_empty_string(mock_message):
    result = await parse("", mock_message)
    assert result == "I didn't understand that. Try `@Simon/help`."

@pytest.mark.asyncio
async def test_whitespace_only(mock_message):
    result = await parse("   ", mock_message)
    assert result == "I didn't understand that. Try `@Simon/help`."

@pytest.mark.asyncio
async def test_at_symbol_only(mock_message):
    result = await parse("@", mock_message)
    assert result == "I didn't understand that. Try `@Simon/help`."

@pytest.mark.asyncio
async def test_missing_slash(mock_message):
    result = await parse("@Simon", mock_message)
    assert result == "I didn't understand that. Try `@Simon/help`."

@pytest.mark.asyncio
async def test_empty_name(mock_message):
    result = await parse("@/help", mock_message)
    assert result == "I didn't understand that. Try `@Simon/help`."

@pytest.mark.asyncio
async def test_empty_command(mock_message):
    result = await parse("@Simon/", mock_message)
    assert result == "I didn't understand that. Try `@Simon/help`."


def get_parsed(mock_handle) -> ParsedCommand:
    return mock_handle.call_args[0][0]


@pytest.mark.asyncio
async def test_name_is_parsed(mock_message, mock_handle):
    await parse("@Simon/help", mock_message)
    assert get_parsed(mock_handle).name == "Simon"

@pytest.mark.asyncio
async def test_command_is_parsed(mock_message, mock_handle):
    await parse("@Simon/help", mock_message)
    assert get_parsed(mock_handle).command == "help"

@pytest.mark.asyncio
async def test_no_args(mock_message, mock_handle):
    await parse("@Simon/help", mock_message)
    assert get_parsed(mock_handle).args == []

@pytest.mark.asyncio
async def test_single_arg(mock_message, mock_handle):
    await parse("@Simon/event-birthday", mock_message)
    assert get_parsed(mock_handle).args == ["birthday"]

@pytest.mark.asyncio
async def test_multiple_args(mock_message, mock_handle):
    await parse("@Simon/event-birthday-saturday-3pm", mock_message)
    assert get_parsed(mock_handle).args == ["birthday", "saturday", "3pm"]

@pytest.mark.asyncio
async def test_leading_trailing_whitespace_stripped(mock_message, mock_handle):
    await parse("   @Simon/help   ", mock_message)
    parsed = get_parsed(mock_handle)
    assert parsed.name == "Simon"
    assert parsed.command == "help"

@pytest.mark.asyncio
async def test_trailing_dashes_stripped_from_args(mock_message, mock_handle):
    await parse("@Simon/event-birthday--", mock_message)
    assert get_parsed(mock_handle).args == ["birthday"]