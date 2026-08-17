# Microservice Conversational Agent

A Kubernetes-deployable LangGraph conversational layer that enables natural-language understanding and safe operation of REST microservices through a semantic Service Digest.

The included Order/Fulfillment service serves as the reference implementation and demonstration domain.

## Showcase goal

> Can a separate runtime agent use a machine-generated semantic service digest to provide a stateful conversational interface to a REST microservice while keeping API execution deterministic, validated, and human-approved for risky actions?

## Architecture

```text
                  LangSmith Studio
                  Chat + Graph UI
                         |
                         v
              LangGraph Agent Server
              namespace: conversational-layer
                         |
                 +-------+--------+
                 |                |
                 v                v
       service-digest.yaml    thread state
                 |                |
                 +-------+--------+
                         v
                   LLM planner
                         |
                         v
                canonical operation
                         |
                         v
             deterministic validator
                         |
                    safety gate
                         |
                 interrupt if needed
                         |
                         v
               deterministic executor
                         |
                         v
       Order/Fulfillment REST Service
       namespace: order-fulfillment
                         |
                         v
                     PostgreSQL
```

## What the agent can do

- answer questions about service purpose and capabilities;
- explain entities, state machines, workflows, business rules, errors, and API methods;
- distinguish stable service knowledge from current runtime data;
- query live customers, products, orders, shipments, returns, refunds, and timelines;
- resolve conversational references across a thread;
- plan multi-call workflows one operation at a time;
- invoke any of the 30 digest-defined operations;
- validate path/query/body inputs against the embedded OpenAPI contract;
- require LangGraph human-in-the-loop confirmation for operations marked risky in the digest;
- interpret backend business errors conversationally.

## Critical execution boundary

The LLM **cannot issue raw HTTP requests**.

It returns only:

```yaml
operation_id: cancel_order
path_params:
  order_id: ORD-123
body:
  reason: Customer changed mind
```

The deterministic runtime retrieves the method/path from the digest, validates the arguments, checks confirmation policy, and then performs the request. Unknown operation IDs are blocked.

## Prerequisites

Your existing lab should already have:

- Ubuntu 24.04 VM
- kubeadm Kubernetes node
- containerd Kubernetes runtime
- Docker available for local image builds
- Calico networking
- running Order/Fulfillment service in namespace `order-fulfillment`
- Order/Fulfillment NodePort health at `http://192.168.253.10:30080/health`

You also need:

- an OpenAI API key for the model;
- a LangSmith account/API key for Studio connectivity.

## Project layout

```text
.
├── digest/
│   └── order-fulfillment-service-digest.yaml
├── docs/
│   ├── ARCHITECTURE.md
│   ├── EXAMPLE_CONVERSATIONS.md
│   ├── SECURITY.md
│   ├── STUDIO.md
│   └── REFERENCES.md
├── k8s/
│   ├── 00-namespace.yaml
│   ├── 01-configmap.yaml
│   ├── 01-secret.example.yaml
│   ├── 02-deployment.yaml
│   └── 03-service.yaml
├── scripts/
├── src/conversational_agent/
├── tests/
├── Dockerfile
├── langgraph.json
└── pyproject.toml
```

# Deploy to your Kubernetes lab

## 1. Verify the existing service

```bash
kubectl get pods,svc -n order-fulfillment
curl -fsS http://192.168.253.10:30080/health
```

## 2. Start Docker if needed

```bash
sudo systemctl start docker
```

## 3. Build and import the agent image into Kubernetes containerd

```bash
./scripts/build-and-load.sh
```

Verify:

```bash
sudo ctr -n k8s.io images list | grep microservice-conversational-agent
```

## 4. Create Kubernetes secrets without writing them to disk

```bash
export OPENAI_API_KEY='...'
export LANGSMITH_API_KEY='...'
./scripts/create-secrets.sh
```

## 5. Deploy

```bash
./scripts/deploy.sh
```

Expected service:

```text
conversational-agent   NodePort   ...   2024:30204/TCP
```

Check:

```bash
curl -fsS http://192.168.253.10:30204/ok
```

## 6. Run smoke tests

Knowledge/digest question:

```bash
./scripts/smoke-knowledge.sh
```

Live read through the Order/Fulfillment API:

```bash
./scripts/smoke-runtime-read.sh
```

Optional command-line human-in-the-loop demo (use an eligible unshipped order ID):

```bash
./scripts/demo-confirmation.sh ORD-...
```

The script runs until the LangGraph interrupt, shows the exact pending operation, and resumes with approve/reject.

# Open in Studio

Recommended from a browser running on the Ubuntu VM:

```bash
./scripts/port-forward.sh
```

Keep that terminal open. Then open:

```text
https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
```

Select the graph/assistant named:

```text
service_agent
```

See `docs/STUDIO.md` for showcase scenarios and browser troubleshooting.

# Local development without Kubernetes

Create an environment and install:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
```

Set `.env` so `ORDER_SERVICE_BASE_URL` points at the existing Order service NodePort, then:

```bash
./scripts/run-local.sh
```

# Tests

```bash
pip install -e '.[dev]'
pytest -q
```

The unit tests do not call the LLM. They validate the digest loader, contract validator, allowlisted REST executor, and confirmation parser.

# Important deployment note

This package intentionally runs **`langgraph dev` in Kubernetes** for the showcase. Current LangGraph documentation describes that Agent Server mode as a development/testing server, while production self-hosted Agent Server deployment uses a different licensed stack with durable backing services. This project therefore demonstrates the agent and Studio experience on your lab cluster without pretending that the dev server is a production deployment.

For a production evolution, replace the showcase Agent Server with a supported production deployment, durable persistence, TLS/Ingress, authentication/authorization, network policies, and proper secret management.
