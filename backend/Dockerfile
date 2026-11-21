FROM python:3.12-slim-bookworm

RUN pip install --no-cache-dir uv==0.11.25

WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
COPY backend/app ./app
RUN uv sync --frozen --no-dev
COPY knowledge ./knowledge

ENV PATH="/app/.venv/bin:$PATH" \
    KNOWLEDGE_DIR=/app/knowledge \
    PYTHONUNBUFFERED=1

EXPOSE 8000
# Local `uv run uvicorn` does not ingest. This command is the container start path.
CMD ["python", "-m", "app.serve"]
