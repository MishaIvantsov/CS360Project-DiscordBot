import os
import re
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

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
    server = HTTPServer(("0.0.0.0", port), CallbackHandler)
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

    text = re.sub(r"<@!?\d+>", "@Simon", message.content).strip()
    response = await command_parser.parse(text, message)
    await message.reply(response)


# --- Startup ---

if __name__ == "__main__":
    from database import init_db

    init_db()

    thread = threading.Thread(target=start_callback_server, daemon=True)
    thread.start()

    port = int(os.environ.get("PORT", 8080))
    print(f"OAuth callback server running on http://0.0.0.0:{port}")

    client.run(os.getenv("DISCORD_TOKEN", ""))
