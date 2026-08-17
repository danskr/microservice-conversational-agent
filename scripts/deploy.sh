#!/usr/bin/env bash
set -euo pipefail

if ! kubectl get svc order-fulfillment-service -n order-fulfillment >/dev/null 2>&1; then
  echo "ERROR: Existing Order/Fulfillment service was not found in namespace order-fulfillment." >&2
  echo "Deploy and verify that service first." >&2
  exit 1
fi

kubectl apply -f k8s/00-namespace.yaml

if ! kubectl get secret conversational-agent-secrets -n conversational-layer >/dev/null 2>&1; then
  echo "ERROR: Kubernetes secret conversational-agent-secrets does not exist." >&2
  echo "Run: export OPENAI_API_KEY=... LANGSMITH_API_KEY=... && ./scripts/create-secrets.sh" >&2
  exit 1
fi

kubectl apply -f k8s/01-configmap.yaml
kubectl apply -f k8s/02-deployment.yaml
kubectl apply -f k8s/03-service.yaml

kubectl rollout status deployment/conversational-agent -n conversational-layer --timeout=180s
kubectl get pods,svc -n conversational-layer

echo
echo "Agent Server health: http://192.168.253.10:30204/ok"
echo "Agent Server docs:   http://192.168.253.10:30204/docs"
echo
echo "Recommended Studio connection from the Ubuntu VM:"
echo "  ./scripts/port-forward.sh"
echo "Then open:"
echo "  https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024"
