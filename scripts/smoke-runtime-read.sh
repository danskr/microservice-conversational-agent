#!/usr/bin/env bash
set -euo pipefail
BASE="${AGENT_BASE_URL:-http://192.168.253.10:30204}"

THREAD_JSON=$(curl -fsS -X POST "${BASE}/threads" -H 'Content-Type: application/json' -d '{}')
THREAD_ID=$(printf '%s' "$THREAD_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["thread_id"])')
echo "Thread: ${THREAD_ID}"

echo "Asking the agent for current products. This should cause a digest-allowlisted GET operation."
curl -fsS -X POST "${BASE}/threads/${THREAD_ID}/runs/wait" \
  -H 'Content-Type: application/json' \
  -d '{
    "assistant_id": "service_agent",
    "input": {
      "messages": [
        {"role": "human", "content": "What products currently exist in the service? Give me their names and SKUs."}
      ]
    }
  }' | python3 -m json.tool
