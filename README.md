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
