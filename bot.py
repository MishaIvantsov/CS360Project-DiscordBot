import asyncio
import logging
import os
import re
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

import discord
from discord import app_commands
from dotenv import load_dotenv

import command_parser
import commands
from auth import exchange_code

load_dotenv()

logger = logging.getLogger(__name__)

COMMAND_TIMEOUT = 20  # seconds; hard cap on how long a command may run

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


# --- OAuth Callback Server ---


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        # --- ADDED: Fly.io Health Check Endpoint ---
        if parsed.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
            return

        params = parse_qs(parsed.query)

        code = params.get("code", [None])[0]
        discord_id = params.get("state", [None])[0]

        if code and discord_id:
            try:
                exchange_code(discord_id, code)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Successfully linked! You can close this tab.")
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Error: {e}".encode())
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Missing code or state.")

    def log_message(self, format, *args):
        pass  # silence default HTTP server logs


def start_callback_server():
    # --- FIXED: Bind to 0.0.0.0 and use Fly's injected PORT ---
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), CallbackHandler)  # nosec B104
    server.serve_forever()


# --- Helpers ---


async def _run(coro):
    """Run a command coroutine with a hard timeout.

    A timeout raises asyncio.TimeoutError, which the tree error handler turns
    into a user-facing message -- so a stalled Google call resolves the
    "thinking..." state instead of hanging forever.
    """
    return await asyncio.wait_for(coro, timeout=COMMAND_TIMEOUT)


def make_embed(title: str, description: str, color=discord.Color.blue()):
    """Build a standard Simon embed."""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
    )
    embed.set_footer(text="Simon Calendar Assistant")
    return embed


# --- Discord Bot ---


@client.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {client.user}")
    print("Slash commands synced.")


# Legacy @Simon mention handler
@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if client.user not in message.mentions:
        return

    text = re.sub(r"<@!?\d+>", "@Simon", message.content).strip()

    try:
        response = await _run(command_parser.parse(text, message))
    except asyncio.TimeoutError:
        response = "⏳ That took too long — please try again."
    except Exception:
        logger.warning("legacy command failed", exc_info=True)
        response = "❌ Couldn't handle that — check your input and try again."

    # Discord rejects empty messages; only reply when there's something to say.
    if response:
        await message.reply(response)


# --- Slash Command Error Handler ---


@tree.error
async def on_app_command_error(
    interaction: discord.Interaction, error: app_commands.AppCommandError
):
    # discord.py wraps the real exception in CommandInvokeError.
    original = getattr(error, "original", error)

    if isinstance(original, asyncio.TimeoutError):
        msg = "⏳ That took too long — please try again."
    else:
        msg = "❌ Couldn't handle that — check your input and try again."

    logger.warning("slash command failed", exc_info=original)

    try:
        if interaction.response.is_done():  # we already deferred / responded
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
    except discord.HTTPException:
        logger.warning("failed to deliver error message", exc_info=True)


# --- Slash Commands ---


@tree.command(name="help", description="Show Simon commands")
async def help_command(interaction: discord.Interaction):
    response = await commands.help_slash()

    await interaction.response.send_message(
        embed=make_embed("Simon Help", response),
        ephemeral=True,
    )


@tree.command(name="link", description="Link your Google Calendar")
async def link_command(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    response = await commands.link_slash(str(interaction.user.id))

    await interaction.followup.send(
        embed=make_embed("Link Google Calendar", response),
        ephemeral=True,
    )


@tree.command(name="unlink", description="Unlink your Google Calendar")
async def unlink_command(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    response = await commands.unlink_slash(str(interaction.user.id))

    await interaction.followup.send(
        embed=make_embed("Unlink Google Calendar", response),
        ephemeral=True,
    )


@tree.command(name="info", description="Show events on a date")
@app_commands.describe(date="Example: 05.20.2026")
async def info_command(interaction: discord.Interaction, date: str):
    await interaction.response.defer()

    response = await _run(commands.info_slash(str(interaction.user.id), date))

    await interaction.followup.send(embed=make_embed("Calendar Info", response))


@tree.command(name="add", description="Add a calendar event")
@app_commands.describe(
    title="Event title",
    date="Example: 05.20.2026",
    time="Example: 12:00 PM",
    location="Event location",
    description="Event description",
)
async def add_command(
    interaction: discord.Interaction,
    title: str,
    date: str,
    time: str,
    location: str,
    description: str,
):
    await interaction.response.defer()

    response = await _run(
        commands.add_slash(
            str(interaction.user.id),
            title,
            date,
            time,
            location,
            description,
        )
    )

    await interaction.followup.send(
        embed=make_embed("Add Event", response, discord.Color.green())
    )


@tree.command(name="edit", description="Edit a calendar event")
@app_commands.describe(
    event_id="Event ID",
    field="Field to edit",
    new_value="New value",
)
@app_commands.choices(
    field=[
        app_commands.Choice(name="title", value="title"),
        app_commands.Choice(name="date", value="date"),
        app_commands.Choice(name="time", value="time"),
        app_commands.Choice(name="location", value="location"),
        app_commands.Choice(name="description", value="description"),
    ]
)
async def edit_command(
    interaction: discord.Interaction,
    event_id: str,
    field: app_commands.Choice[str],
    new_value: str,
):
    await interaction.response.defer()

    response = await _run(
        commands.edit_slash(
            str(interaction.user.id),
            event_id,
            field.value,
            new_value,
        )
    )

    await interaction.followup.send(embed=make_embed("Edit Event", response))


@tree.command(name="delete", description="Delete a calendar event")
@app_commands.describe(event_id="Event ID")
async def delete_command(interaction: discord.Interaction, event_id: str):
    await interaction.response.defer()

    response = await _run(commands.delete_slash(str(interaction.user.id), event_id))

    await interaction.followup.send(
        embed=make_embed("Delete Event", response, discord.Color.red())
    )


# --- Startup ---


if __name__ == "__main__":
    from database import init_db

    init_db()

    thread = threading.Thread(target=start_callback_server, daemon=True)
    thread.start()

    port = int(os.environ.get("PORT", 8080))
    print(f"OAuth callback server running on http://0.0.0.0:{port}")

    client.run(os.getenv("DISCORD_TOKEN", ""))
