from __future__ import annotations
import discord
from command_parser import ParsedCommand
from calendar_api import get_events_by_date, add_event, Event, EVENTS
 
 
@dataclass
class ParsedCommand:
    name: str
    command: str
    args: list[str] = field(default_factory=list)
 
 
async def parse(text: str, message: discord.Message) -> str:
    text = text.strip()
    if not text.startswith("@"):
        return "I didn't understand that. Try `@Simon/help`."
 
    body = text[1:]
    if "/" not in body:
        return "I didn't understand that. Try `@Simon/help`."
 
    name, rest = body.split("/", 1)
    if not name or not rest:
        return "I didn't understand that. Try `@Simon/help`."
 
    parts = rest.split("-")
    command, *args = parts
    if not command:
        return "I didn't understand that. Try `@Simon/help`."
 
    while args and args[-1] == "":
        args.pop()
 
    parsed = ParsedCommand(name=name, command=command, args=args)
    return await commands.handle(parsed, message)

async def help_cmd(args: list[str], message: discord.Message) -> str:
    return (
        "**Simon Bot Commands:**\n"
        "`@Simon/info-<MM.DD.YYYY>` — list events on a date\n"
        "`@Simon/add-<title>-<date>-<time>-<location>-<description>` — add event\n"
        "`@Simon/edit-<id>-<field>-<value>` — edit an event\n"
        "`@Simon/delete-<id>` — delete an event"
    )