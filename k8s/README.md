# Kubernetes resources

Namespace: `conversational-layer`

Resources:
- ConfigMap: runtime configuration and Order service cluster DNS
- Deployment: one showcase Agent Server replica
- NodePort Service: `30204 -> 2024`
- Secret: created separately by `scripts/create-secrets.sh`

The deployment intentionally runs `langgraph dev` inside the pod. This gives the project the Agent Server protocol required by Studio without requiring the licensed production standalone LangSmith deployment stack. It is for a lab/showcase, not production.

The local Agent Server persists development checkpoint data under `.langgraph_api`; this is mounted to `emptyDir`. Conversation state therefore survives a container restart in the same pod but is lost when the pod is replaced.
