#!/usr/bin/env bash
set -euo pipefail

: "${OPENAI_API_KEY:?Export OPENAI_API_KEY before running this script}"
: "${LANGSMITH_API_KEY:?Export LANGSMITH_API_KEY before running this script}"

kubectl apply -f k8s/00-namespace.yaml

kubectl -n conversational-layer create secret generic conversational-agent-secrets \
  --from-literal=OPENAI_API_KEY="${OPENAI_API_KEY}" \
  --from-literal=LANGSMITH_API_KEY="${LANGSMITH_API_KEY}" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "Secret conversational-agent-secrets created/updated without writing keys to project files."
