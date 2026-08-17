#!/usr/bin/env bash
set -euo pipefail

echo "Forwarding local http://127.0.0.1:2024 to the Kubernetes Agent Server."
echo "Keep this terminal open, then visit:"
echo "https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024"
echo
kubectl -n conversational-layer port-forward service/conversational-agent 2024:2024
