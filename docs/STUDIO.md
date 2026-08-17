# LangSmith Studio Showcase

## Why Studio

Studio is used as the technical showcase UI because it can display both the chat and the LangGraph execution path/state.

## Recommended connection on the Ubuntu VM

After deployment:

```bash
./scripts/port-forward.sh
```

Keep the terminal open. In a browser on the same Ubuntu VM, open:

```text
https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
```

Sign in to LangSmith if prompted and select the `service_agent` graph.

If the browser blocks the connection, use Studio's **Connect to a local server** flow and explicitly allow `http://127.0.0.1:2024`. Browser private-network/mixed-content rules can change; port-forwarding to localhost is more reliable than connecting Studio directly to the Kubernetes NodePort.

## Good demo prompts

### Knowledge only

```text
What does this service do?
```

```text
Explain the order lifecycle and tell me when cancellation is allowed.
```

```text
What is the difference between inventory allocation and shipment?
```

### Runtime reads

```text
What products currently exist? Show their SKUs and available stock.
```

```text
Show me the latest five orders.
```

```text
What happened to order ORD-... ?
```

### Multi-step reasoning

```text
Find the newest order and tell me whether it can still be cancelled.
```

The graph should use one or more read operations and then explain the result.

### Human-in-the-loop

Create/identify an eligible order, then ask:

```text
Cancel that order because the customer changed their mind.
```

The graph should resolve the concrete order ID, reach `safety_gate`, and pause with an interrupt before calling `cancel_order`.

## What to show in a portfolio demo

1. Chat view: natural-language request.
2. Graph view: `decide -> validate_call -> safety_gate -> execute_call`.
3. Interrupt payload: exact operation, target ID, risk, and body.
4. Resume with approval.
5. Final natural-language explanation based on the API result.
