# Simon — Discord Calendar Bot

A Discord bot that lets users manage their Google Calendar directly from chat. Each user authenticates with their own Google account through OAuth 2.0, so all events are read from and written to that user's personal calendar.

**Live deployment:** [https://simon-bot.fly.dev/health](https://simon-bot.fly.dev/health) (returns `ok` when the bot is online)

---

## What Simon Does

Simon is a Discord chatbot built with `discord.py` that wraps the Google Calendar API. Once a user runs `@Simon/link` and authorizes their Google account, Simon can:

- List the events on any date
- Create a new event
- Edit an existing event (title, date, time, location, description)
- Delete an event

Each Discord user's OAuth refresh token is stored in a SQLite database, keyed by their Discord ID, so the bot can act on the right person's calendar without ever holding a shared service account.

---


## Command Reference

All commands are triggered by mentioning the bot in a Discord channel. The format is always `@Simon/<command>-<arg1>-<arg2>-...`.

| Command | What it does |
|---|---|
| `@Simon/help` | Show all commands |
| `@Simon/link` | Connect your Google Calendar (returns a one-time OAuth link) |
| `@Simon/unlink` | Remove your stored credentials |
| `@Simon/info-<MM.DD.YYYY>` | List events on a given date |
| `@Simon/add-<title>-<date>-<time>-<location>-<description>` | Create an event |
| `@Simon/edit-<event_id>-<field>-<new_value>` | Edit an event (field = title, date, time, location, or description) |
| `@Simon/delete-<event_id>` | Delete an event |

**Example:** `@Simon/info-05.21.2026`

---

## Architecture

Simon is organized as a pipeline of focused modules:

```
Discord message
      ↓
   bot.py              (Discord client + OAuth callback HTTP server)
      ↓
command_parser.py      (Parses raw text into a ParsedCommand)
      ↓
   commands.py         (Routes commands to handlers, formats responses)
      ↓
calendar_api.py        (Wraps Google Calendar — read, create, edit, delete)
      ↓
   Google Calendar
```

Supporting modules:
- **`auth.py`** — The Google OAuth 2.0 flow: generate auth URLs, exchange codes for tokens, refresh expired tokens.
- **`database.py`** — SQLite token persistence. One row per Discord user.

### Tech Stack

- **Language:** Python 3.13
- **Discord library:** `discord.py`
- **Google integration:** `google-auth-oauthlib`, `google-api-python-client`
- **Database:** SQLite (persisted on a Fly.io volume at `/data/tokens.db`)
- **Hosting:** Fly.io (Docker container, region `sjc`)
- **CI/CD:** GitHub Actions

---

## Deployment & CI/CD

Simon is deployed to [Fly.io](https://fly.io) as a Dockerized service. The CI/CD pipeline lives in `.github/workflows/ci-cd.yml` and runs on every push and pull request.

### Pipeline Stages

| Stage | What it does | Runs on |
|---|---|---|
| `lint` | Black (formatter check), Flake8 (linter), Bandit (security scanner) | All branches |
| `test` | Unit, integration, and smoke test suites via `pytest` | All branches |
| `deploy` | `flyctl deploy --remote-only` — builds the Docker image on Fly's builders and ships it | `main` only |
| `verify` | Curls the live `/health` endpoint to confirm the new deployment is reachable | `main` only |

Every job begins with actions/checkout@v4, which pulls the latest code from the target branch.

### How to Trigger a Deploy

**Automatic:** Any push or merged PR to `main` triggers the full pipeline.

**Manual (one-touch from terminal):**
```powershell
.\deploy.ps1
```

`deploy.ps1` pushes `main`, tails the GitHub Actions run with `gh run watch`, and confirms the live `/health` endpoint returns 200.

### Verifying a Deploy

- **GitHub Actions tab** — the `verify` job at the end of the pipeline curls `/health` and fails the run if it doesn't come back 200.
- **Manual check:** `curl https://simon-bot.fly.dev/health` should return `ok`.
- **Bot presence:** Simon shows up online in our Discord server within ~30 seconds of a successful deploy.

### Rolling Back

```powershell
flyctl releases             # list past releases
flyctl releases rollback    # roll back to the previous release
```

---

## Environment Setup (one-time, for new contributors)

1. **Install `flyctl`:**
   ```powershell
   iwr https://fly.io/install.ps1 -useb | iex
   flyctl auth login
   ```
2. **Install the GitHub CLI** (for the one-touch deploy script):
   ```powershell
   winget install GitHub.cli
   gh auth login
   ```
3. **Add the Fly API token to GitHub Secrets:**
   ```powershell
   flyctl tokens create deploy --expiry 720h
   ```
   Copy the output, then in the GitHub repo go to **Settings → Secrets and variables → Actions** and add a new secret named `FLY_API_TOKEN`.
4. **Set the runtime secrets on Fly:**
   ```powershell
   flyctl secrets set DISCORD_TOKEN=<your-discord-token>
   flyctl secrets set OAUTH_REDIRECT_URI=https://simon-bot.fly.dev/oauth/callback
   $b64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes("client_secrets.json"))
   flyctl secrets set GOOGLE_CLIENT_SECRETS_B64=$b64
   ```
5. **Update Google Cloud Console** — under APIs & Services → Credentials → your OAuth client, add `https://simon-bot.fly.dev/oauth/callback` to the authorized redirect URIs.

---

## Local Development

```powershell
git clone https://github.com/MishaIvantsov/CS360Project-DiscordBot.git
cd CS360Project-DiscordBot

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements/requirements.txt
pip install -r requirements/requirements-dev.txt

# Fill in .env with DISCORD_TOKEN and place client_secrets.json next to bot.py
python bot.py
```

The local OAuth callback runs on `http://localhost:8080` — make sure that URL is also in your Google Cloud Console authorized redirect URIs for local testing.

---

## Testing

The test suite is organized into three tiers under `tests/`:

```powershell
pytest tests/unit            # Pure unit tests, no external services
pytest tests/integration     # Multi-module tests with mocked Google API
pytest tests/smoke           # Startup sanity checks (imports, intents, event handlers)
```

Or run the whole suite:

```powershell
pytest tests/
```

Static analysis tools (matching CI):

```powershell
python -m black --check .
python -m flake8 .
python -m bandit -r . -c pyproject.toml
```

---

## Project Structure

```
.
├── .github/workflows/
│   └── ci-cd.yml              # GitHub Actions pipeline
├── requirements/
│   ├── requirements.txt       # Runtime dependencies
│   └── requirements-dev.txt   # Linting + test dependencies
├── tests/
│   ├── unit/                  # Per-module unit tests
│   ├── integration/           # OAuth flow integration tests
│   ├── smoke/                 # Startup sanity tests
│   └── conftest.py            # Shared pytest fixtures
├── auth.py                    # Google OAuth 2.0 flow
├── bot.py                     # Discord client + callback server entry point
├── calendar_api.py            # Google Calendar API wrapper
├── command_parser.py          # Raw message → ParsedCommand
├── commands.py                # Command handlers + dispatch
├── database.py                # SQLite token persistence
├── Dockerfile                 # Container build instructions
├── entrypoint.sh              # Decodes client_secrets.json from env, starts bot
├── fly.toml                   # Fly.io deployment config
├── deploy.ps1                 # One-touch deploy script
├── pyproject.toml             # Black, pytest, bandit config
└── README.md                  # You are here :)
```

---

## Team

CS 360 — Software Engineering, University of Washington

- Misha Ivantsov
- Abdiwali Shaie
- Johnny Han
- Sesen Kiflom
- Aiden Knowles

## CI/CD Pipeline Guide

This project uses GitHub Actions for continuous integration and deployment to Fly.io. The pipeline is defined in `.github/workflows/ci-cd.yml`.

### How it Works
1. **Linting & Testing (All Branches):** Whenever code is pushed or a Pull Request is opened, GitHub Actions automatically provisions an Ubuntu environment, installs dependencies, and runs `black`, `flake8`, `bandit`, and `pytest` (Unit, Integration, Smoke).
2. **Deployment (Main Branch Only):** If code is pushed or merged into the `main` branch, the pipeline builds a Docker container and deploys the bot to Fly.io.
3. **Verification:** Post-deployment, the pipeline pings the `0.0.0.0/health` endpoint to ensure the container is running and accessible.

### How to Set Up the Environment
To run this pipeline on a new fork or repository, you must configure the following Repository Secrets in GitHub (`Settings` -> `Secrets and variables` -> `Actions`):

* `FLY_API_TOKEN`: Your personal access token from Fly.io (generated via `flyctl tokens create`).
* `DISCORD_TOKEN`: The authentication token for the Discord bot application.

Once these secrets are set, simply push to the `main` branch to trigger a full build and deployment.
