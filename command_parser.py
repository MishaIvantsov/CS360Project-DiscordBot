from __future__ import annotations
from dataclasses import dataclass, field
import discord
import commands


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
