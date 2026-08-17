#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f .env ]]; then
  echo "Create .env from .env.example and fill in OPENAI_API_KEY and LANGSMITH_API_KEY first." >&2
  exit 1
fi

exec langgraph dev --host 0.0.0.0 --port 2024 --no-browser
