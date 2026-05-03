# Source filter semantics (ADR-030 Stage 3)

Rules use a XOR pair to scope which transactions they apply to:

- `source_type: "<type>"` — rule applies to **every** transaction of that type. Example: `source_type: "kbank"` matches any kbank account.
- `source_id: <int>` — rule applies only to that **specific account instance**. Use the id from `mcp__lurii-finance__list_sources`.
- both omitted — catch-all (matches every transaction).

Pick by intent:
- Type filter for cross-account behavior (e.g. all kbank monthly statements).
- `source_id` for an account-specific quirk (e.g. one wise account that uses a different `_balance_direction` field).

The legacy `source` parameter is still accepted as a deprecation alias — auto-resolved against `sources` (matches `sources.name` → `source_id`, anything else → `source_type`). Prefer the explicit pair.

Before authoring an instance-pinned rule, call `mcp__lurii-finance__list_sources` to enumerate `(id, name, type, tx_count, snap_count)`.
