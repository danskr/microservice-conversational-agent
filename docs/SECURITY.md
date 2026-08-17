# Safety and Security Model

This is a showcase/lab project, but the execution boundary is deliberately strict.

1. **Operation allowlist** — only IDs present in `service-digest.yaml` are executable.
2. **No arbitrary URLs** — method and path are never accepted from model output.
3. **Single target service** — requests are always rooted at `ORDER_SERVICE_BASE_URL`.
4. **Schema validation** — path/query/body input is checked against the contract in the digest before network I/O.
5. **Confirmation enforcement** — high-risk/destructive/financial operations marked required are paused with a LangGraph interrupt.
6. **Concrete confirmation** — the interrupt exposes resolved IDs and body values, so approval applies to a specific call.
7. **No secret knowledge** — the digest intentionally contains no Kubernetes Secrets or database credentials.
8. **Service-side business rules remain authoritative** — the Order/Fulfillment service still enforces its own state and business rules. The agent does not bypass them.

## Not production security

The showcase deployment exposes the development Agent Server with a NodePort and does not configure end-user authentication. Do not expose it to an untrusted network. A production version would add Agent Server authentication, network policy, TLS/Ingress, durable persistence, secrets management, authorization scopes, audit storage, and rate limiting.
