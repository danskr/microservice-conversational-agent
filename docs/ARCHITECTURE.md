# Architecture

## Purpose

This project is Phase 2 of the conversational microservice experiment. It receives exactly one canonical artifact from Phase 1: `digest/order-fulfillment-service-digest.yaml`. The runtime agent does not inspect the original Order/Fulfillment Python source, OpenAPI file, README, tests, or Kubernetes manifests.

## Runtime flow

```text
User / LangSmith Studio
        |
        v
LangGraph Agent Server
        |
        v
+---------------------------+
| prepare_turn              |
+-------------+-------------+
              |
              v
+---------------------------+
| decide                    |
| LLM + focused digest      |
+-------------+-------------+
              |
      +-------+-------+
      |               |
      v               v
 answer/clarify      invoke
      |               |
      v               v
     END       validate_call
                      |
                      v
                 safety_gate
                  /       \
             interrupt    no confirmation
                |             |
                +------v------+
                       |
                       v
                 execute_call
                       |
                       v
                    decide
```

## Responsibility boundary

### LLM planner

The model may:
- interpret natural language;
- answer from digest semantics;
- choose one canonical operation ID;
- supply path/query/body arguments;
- use API results to plan another operation;
- ask for clarification.

The model may not:
- supply an HTTP method;
- supply an arbitrary URL;
- bypass digest confirmation policy;
- execute code;
- access Kubernetes Secrets or PostgreSQL directly.

### Deterministic runtime

The runtime:
- verifies the operation exists in the digest;
- validates parameters/body against the embedded OpenAPI contract;
- obtains method/path only from the digest;
- applies confirmation policy from the digest;
- URL-encodes resolved path parameters;
- invokes only the configured Order/Fulfillment base URL;
- records API results in graph state.

## Conversation state

The Agent Server owns thread persistence. The graph intentionally compiles without its own checkpointer because Agent Server injects checkpointing and storage. The graph stores:
- messages;
- active entity IDs discovered from API responses;
- API history;
- current decision;
- current/last API result;
- per-turn execution trace.

This enables follow-ups such as:

```text
User: Show me my latest order.
Agent: ... ORD-123 ...
User: Has it shipped?
Agent: ...
User: Cancel it.
```

## Human-in-the-loop

Operations marked `confirmation: required` in the digest trigger a LangGraph `interrupt()` containing the exact resolved operation and arguments. Execution resumes only when the interrupt response is an explicit approval.

Conditional confirmation follows the digest rule: it is required when arguments are inferred, confidence is low, or `CONFIRM_CONDITIONAL_ACTIONS=true`.
