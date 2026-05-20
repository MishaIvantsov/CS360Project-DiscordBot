import importlib
import inspect

import pytest


@pytest.mark.parametrize(
    "module",
    [
        "auth",
        "bot",
        "calendar_api",
        "command_parser",
        "commands",
        "database",
    ],
)
def test_module_imports(module):
    """Every top-level module imports cleanly."""
    importlib.import_module(module)


def test_message_content_intent_enabled():
    """The bot needs message_content to read @Simon mentions."""
    import bot

    assert bot.intents.message_content is True


def test_event_handlers_registered():
    """on_ready and on_message are wired up to the client via @client.event."""
    import bot

    # @client.event does setattr(client, coro.__name__, coro), so the
    # registered handler should be the same function object we defined.
    assert getattr(bot.client, "on_ready", None) is bot.on_ready
    assert getattr(bot.client, "on_message", None) is bot.on_message
    assert inspect.iscoroutinefunction(getattr(bot.client, "on_message"))
