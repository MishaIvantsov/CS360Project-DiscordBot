#!/bin/sh
set -e

if [ -n "$GOOGLE_CLIENT_SECRETS_B64" ]; then
    echo "$GOOGLE_CLIENT_SECRETS_B64" | base64 -d > /app/client_secrets.json
fi

exec python bot.py