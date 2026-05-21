FROM python:3.13-slim

WORKDIR /app

# System deps — slim image needs build tools for some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first for better layer caching
COPY requirements/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY . .

# Volume mount point for the SQLite database
RUN mkdir -p /data
ENV DB_PATH=/data/tokens.db

# OAuth callback server port (Fly injects PORT at runtime)
ENV PORT=8080
EXPOSE 8080

# Entrypoint reconstructs client_secrets.json from a base64 env var, then runs the bot
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
CMD ["/entrypoint.sh"]