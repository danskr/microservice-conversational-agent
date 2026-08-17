#!/usr/bin/env bash
set -euo pipefail

BASE="${AGENT_BASE_URL:-http://192.168.253.10:30204}"
ORDER_ID="${1:-}"
if [[ -z "$ORDER_ID" ]]; then
  echo "Usage: $0 ORD-..." >&2
  echo "Choose an unshipped order that is eligible for cancellation." >&2
  exit 2
fi

THREAD_JSON=$(curl -fsS -X POST "${BASE}/threads" -H 'Content-Type: application/json' -d '{}')
THREAD_ID=$(printf '%s' "$THREAD_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["thread_id"])')
echo "Thread: ${THREAD_ID}"

PAYLOAD=$(python3 - "$ORDER_ID" <<'PY'
import json, sys
order_id=sys.argv[1]
print(json.dumps({
  "assistant_id":"service_agent",
  "input":{"messages":[{"role":"human","content":f"Cancel order {order_id} because the customer changed their mind."}]}
}))
PY
)

RESULT=$(curl -fsS -X POST "${BASE}/threads/${THREAD_ID}/runs/wait" \
  -H 'Content-Type: application/json' \
  -d "$PAYLOAD")

echo "$RESULT" | python3 -m json.tool

HAS_INTERRUPT=$(printf '%s' "$RESULT" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("yes" if d.get("__interrupt__") else "no")')
if [[ "$HAS_INTERRUPT" != "yes" ]]; then
  echo "No confirmation interrupt was returned. Inspect the output above." >&2
  exit 1
fi

read -r -p "Approve the exact interrupted operation? [y/N] " ANSWER
if [[ ! "$ANSWER" =~ ^[Yy]$ ]]; then
  RESUME='{"assistant_id":"service_agent","command":{"resume":"reject"}}'
else
  RESUME='{"assistant_id":"service_agent","command":{"resume":"approve"}}'
fi

curl -fsS -X POST "${BASE}/threads/${THREAD_ID}/runs/wait" \
  -H 'Content-Type: application/json' \
  -d "$RESUME" | python3 -m json.tool
