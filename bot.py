import os
import re
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from commands import PollView, ClosedPollView

import discord
from dotenv import load_dotenv

import command_parser
from auth import exchange_code

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)


# --- OAuth Callback Server ---


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
        pass  # silence default HTTP server logs


def start_callback_server():
    server = HTTPServer(("localhost", 8080), CallbackHandler)
    server.serve_forever()


# --- Discord Bot ---


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")


@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    if client.user not in message.mentions:
        return


@client.event
async def on_interaction(interaction: discord.Interaction):
    await client.process_application_commands(interaction)

    text = re.sub(r"<@!?\d+>", "@Simon", message.content).strip()
    response = await command_parser.parse(text, message)
    await message.reply(response)


# --- Startup ---

if __name__ == "__main__":
    from database import init_db

    init_db()

    client.add_view(PollView("", None))
    client.add_view(ClosedPollView())

    thread = threading.Thread(target=start_callback_server, daemon=True)
    thread.start()
    print("OAuth callback server running on http://localhost:8080")

    client.run(os.getenv("DISCORD_TOKEN", ""))
