from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class ParsedCommand:
    name: str
    command: str
    args: list[str] = field(default_factory=list)


def parse(text: str) -> ParsedCommand | None:
    text = text.strip()

    if not text.startswith("@"):
        return None

    body = text[1:]
    if "/" not in body:
        return None

    name, rest = body.split("/", 1)
    if not name or not rest:
        return None

    parts = rest.split("-")
    command, *args = parts

    if not command:
        return None

    while args and args[-1] == "":
        args.pop()

    return ParsedCommand(name=name, command=command, args=args)