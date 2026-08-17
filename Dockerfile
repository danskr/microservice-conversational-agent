FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
COPY digest ./digest
COPY langgraph.json ./langgraph.json

RUN pip install --upgrade pip && pip install .

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/.langgraph_api \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 2024

# This is intentionally the LangGraph in-memory/dev Agent Server so the project
# can connect directly to Studio without requiring the licensed standalone stack.
# It is suitable for this showcase/lab, not a production Agent Server deployment.
CMD ["langgraph", "dev", "--host", "0.0.0.0", "--port", "2024", "--no-browser", "--no-reload"]
