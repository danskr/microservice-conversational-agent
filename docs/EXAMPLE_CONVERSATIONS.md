# Example Showcase Conversations

These are suggested scenarios, not hard-coded responses.

## Service understanding

**User:** What does this service do?

Expected behavior: answer exclusively from the digest; no REST call.

## API discovery

**User:** Which operations can change order state?

Expected behavior: explain relevant operations and their risk/confirmation policy from the digest.

## Current runtime data

**User:** What products are currently available?

Expected behavior: invoke `list_products`, then summarize the live response.

## Contextual reference

**User:** Show me the latest order.

Expected behavior: invoke `list_orders` with a small limit.

**User:** What is its payment status?

Expected behavior: resolve `it` using thread state and, if needed, invoke `get_order`.

## Multi-step action with confirmation

**User:** Cancel my latest order because the customer changed their mind.

Expected behavior:
1. invoke `list_orders` to resolve the target if no ID is already active;
2. select `cancel_order` with the resolved ID and reason;
3. pause at `safety_gate` because the digest says confirmation is required;
4. display concrete operation arguments;
5. execute only after approval;
6. interpret success or a business-rule error conversationally.

## Business error handling

**User:** Cancel an order that has already shipped.

Expected behavior: the backend rejects it using its own business rules. The agent should explain the service error and, where supported by the digest, suggest the return workflow after delivery rather than silently attempting another destructive operation.
