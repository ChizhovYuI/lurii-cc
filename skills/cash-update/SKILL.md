---
name: cash-update
description: Update the user's manual cash balance via lurii-finance MCP. Reads current balances, asks per-currency amounts, confirms a before/after diff, then calls set_cash_balance. Use when the user says "update cash", "set my cash", "I have $X in cash", "log cash", "add cash balance", or invokes /cash-update.
---

# Cash Update

Mechanism only. Drives the `lurii-finance` MCP cash tools through a confirm-before-write flow. **Read current balance first. Confirm the diff. Halt loud on missing cash source.**

**Requires `pfm-mcp` >= 0.22.9** (cash MCP tools `list_supported_fiat_currencies`, `get_cash_balance`, `set_cash_balance`). On older builds the tool calls in Step 0 will fail with "Unknown tool" — halt and instruct the user to upgrade `lurii-pfm`.

## Hard rules

1. **Never write without confirming.** Show a before/after diff and get explicit "yes" via `AskUserQuestion` before calling `set_cash_balance`.
2. **Never invent amounts.** If the user gives a partial spec (one currency only), preserve unstated currencies at their current values — do not zero them.
3. **Currency codes only from the supported list.** Pull from `list_supported_fiat_currencies`. Reject anything else with the supported list shown.
4. **Decimal strings, not floats.** Pass `"100.50"`, not `100.5` — the MCP tool parses strings and rejects non-finite values.
5. **Halt on missing cash source.** If `get_cash_balance` returns `Cash source not found`, do not try to create one — surface the exact `pfm source add` instruction.
6. **One snapshot per day.** `set_cash_balance` upserts today's row; re-running the skill same day overwrites today, not appends.
7. **Don't refresh other sources.** This skill only touches the cash source. Refreshing crypto/banks is `pfm refresh` (separate).

## Step 0 — Resolve current state

Call in parallel:

1. `mcp__lurii-finance__list_supported_fiat_currencies`
2. `mcp__lurii-finance__get_cash_balance`

Branches:

- Response contains `error: "Cash source not found"` → halt with:

  > No cash source is configured. Run `pfm source add` and pick the `cash` type at the prompt; set `fiat_currencies` to a comma-separated list (e.g. `USD,EUR`). Then re-invoke /cash-update.

- Response contains `error: "Multiple cash sources are configured"` with `matches: [...]` → halt with:

  > Multiple cash sources detected: `<matches joined>`. The MCP cash tool requires exactly one. Delete the extras with `pfm source delete <name>`, then re-invoke /cash-update.

- Response is a `CashBalanceView` → continue.

## Step 1 — Show current state

Render a compact table the user can read at a glance:

```
Current cash (source: <source_name>, last snapshot: <latest_snapshot_date or "never">)

  USD   1,234.56   ($1,234.56)
  EUR     850.00   ($935.00 @ 1.10)
  GBP       0.00   (-)
```

If `latest_snapshot_date` is `null` or older than today, note that — the user may want to refresh stale fiat prices by simply re-saving.

## Step 2 — Collect intent

`AskUserQuestion` (single call), options:

- `update one currency` — fastest path
- `update multiple currencies` — iterate
- `add a new currency` — picks from supported set minus already-selected
- `remove a currency` — drops from `selected_currencies` and zeros it
- `cancel` — exit, no write

Free-text "Other" is auto-provided; treat free-text as a goal description and re-route to one of the above.

## Step 3 — Collect amounts

For each affected currency:

1. Confirm the **currency code** — must be in the supported list. If the user typed `usd`, normalize to `USD` (the MCP tool does too, but check early to fail fast with a helpful message).
2. Ask the **new amount** as a numeric string. Accept comma or dot decimal separator; normalize to dot. Strip thousands separators.
3. Reject negative or non-finite values immediately. Do not pass them to the MCP — the error message is clearer when produced here.

For "add a new currency", the new code joins `selected_currencies`. For "remove", it gets dropped from `selected_currencies` and the amount is set to `"0"` (zero row preserved per `set_cash_balance` semantics — currencies previously held but unselected get zeroed automatically by the tool).

For "update multiple currencies": loop until the user picks "done" via a second `AskUserQuestion`.

## Step 4 — Build the payload

Compose the call args for `set_cash_balance`:

- `selected_currencies`: the final list (existing - removed + added). Order: existing order with new codes appended.
- `balances`: dict with **every** currency in `selected_currencies` as a key. For unchanged currencies, copy the current `amount` from Step 0. For changed/new, use the user's input. The MCP tool zeros out previously-held currencies that are no longer selected — relying on that, do not include removed codes in `balances`.

## Step 5 — Confirm the diff

Render before/after side by side:

```
Diff:
  USD    1,234.56  →  1,234.56   (no change)
  EUR      850.00  →  1,000.00   (+150.00)
  GBP        0.00  →    250.00   (new)
  THB      500.00  →      0.00   (removed)
```

`AskUserQuestion`: **Apply this update?** options: `apply`, `cancel`. Default no recommendation — the user must pick.

If `cancel` → exit cleanly, no write.

## Step 6 — Write

Call `mcp__lurii-finance__set_cash_balance` with the args from Step 4.

Handle errors:

- `error` field present → surface the message verbatim. Do not retry. Common cases:
  - `selected_currencies contains unsupported currencies: …` — re-route to Step 3 with the offending codes flagged.
  - `Amount for 'X' must be non-negative` / `… must be finite` — same.
  - `Invalid amount for 'X'` — same.
- Success response → continue.

## Step 7 — Closeout

Show a one-paragraph summary:

- Source name and snapshot date.
- New per-currency balances and resolved USD values from the response's `balances` map.
- New total USD across all currencies.
- Note if any currency was zeroed out as a result of removal.

End with a hint: the SwiftUI app refreshes automatically (the MCP write triggers a `snapshot_updated` WebSocket event when the daemon is running). If the daemon is not running, the next `pfm refresh` or app open will pick it up.

## Failure modes to avoid

- **Don't write without confirmation.** Step 5 is mandatory even if the user invoked the skill with explicit values.
- **Don't pass float literals.** All amounts are decimal strings.
- **Don't drop unstated currencies.** A partial update preserves the rest.
- **Don't fabricate currency codes.** Only codes from `list_supported_fiat_currencies` are valid.
- **Don't retry on validation errors.** Loop back to Step 3 with the user, don't auto-correct.
- **Don't try to create the cash source from inside the skill.** The Step 0 halt instruction is the correct path.
- **Don't write to `memory/`.** Cash balance lives in the SQLite DB via the MCP, not in workspace memory.
