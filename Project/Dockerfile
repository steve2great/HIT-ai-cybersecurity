# Matches the official course Lab 3 Dockerfile pattern (uv-based, no rebuild
# needed for source edits because compose.yml mounts the project at /app).
FROM astral/uv:python3.11-trixie

WORKDIR /chainlit-runtime
COPY pyproject.toml ./
RUN uv sync --no-dev --no-install-project

ENV PATH="/chainlit-runtime/.venv/bin:${PATH}"
EXPOSE 8000
