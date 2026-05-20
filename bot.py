import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

import discord
from discord import app_commands
from dotenv import load_dotenv

import commands
from auth import exchange_code

load_dotenv()

intents = discord.Intents.default()

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
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
        pass


def start_callback_server():
    server = HTTPServer(("localhost", 8080), CallbackHandler)
    server.serve_forever()


def make_embed(title: str, description: str, color=discord.Color.blue()):
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
    )
    embed.set_footer(text="Simon Calendar Assistant")
    return embed


@client.event
async def on_ready():
    await tree.sync()

    print(f"Logged in as {client.user}")
    print("Slash commands synced.")


@tree.command(name="help", description="Show Simon commands")
async def help_command(interaction: discord.Interaction):
    response = await commands.help_cmd()

    await interaction.response.send_message(
        embed=make_embed("Simon Help", response),
        ephemeral=True,
    )


@tree.command(name="link", description="Link your Google Calendar")
async def link_command(interaction: discord.Interaction):

    await interaction.response.defer(ephemeral=True)

    discord_id = str(interaction.user.id)

    response = await commands.link(discord_id)

    await interaction.followup.send(
        embed=make_embed("Link Google Calendar", response),
        ephemeral=True,
    )


@tree.command(name="unlink", description="Unlink your Google Calendar")
async def unlink_command(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    discord_id = str(interaction.user.id)

    response = await commands.unlink(discord_id)

    await interaction.followup.send(
        embed=make_embed("Unlink Google Calendar", response),
        ephemeral=True,
    )


@tree.command(name="info", description="Show events on a date")
@app_commands.describe(date="Example: 05.20.2026")
async def info_command(interaction: discord.Interaction, date: str):
    discord_id = str(interaction.user.id)

    await interaction.response.defer()

    response = await commands.info(discord_id, date)

    await interaction.followup.send(embed=make_embed("Calendar Info", response))


@tree.command(name="add", description="Add a calendar event")
@app_commands.describe(
    title="Event title",
    day="Day",
    month="Month",
    year="Year",
    time="Example: 12:00 PM",
    location="Event location",
    description="Event description",
)
async def add_command(
    interaction: discord.Interaction,
    title: str,
    month: int,
    day: int,
    year: int,
    time: str,
    location: str,
    description: str,
):
    discord_id = str(interaction.user.id)

    await interaction.response.defer()

    response = await commands.add(
        discord_id,
        title,
        day,
        month,
        year,
        time,
        location,
        description,
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
    discord_id = str(interaction.user.id)

    await interaction.response.defer()

    response = await commands.edit(
        discord_id,
        event_id,
        field.value,
        new_value,
    )

    await interaction.followup.send(embed=make_embed("Edit Event", response))


@tree.command(name="delete", description="Delete a calendar event")
@app_commands.describe(event_id="Event ID")
async def delete_command(interaction: discord.Interaction, event_id: str):
    discord_id = str(interaction.user.id)

    await interaction.response.defer()

    response = await commands.delete(discord_id, event_id)

    await interaction.followup.send(
        embed=make_embed("Delete Event", response, discord.Color.red())
    )


if __name__ == "__main__":
    from database import init_db

    init_db()

    thread = threading.Thread(target=start_callback_server, daemon=True)
    thread.start()

    print("OAuth callback server running on http://localhost:8080")

    client.run(os.getenv("DISCORD_TOKEN", ""))
