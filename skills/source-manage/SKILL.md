---
name: source-manage
description: Add, edit, rename, or delete data sources in the lurii-finance MCP. Wraps add_source / update_source / delete_source / get_source_schema with confirm-before-write flows. Use when the user says "add a source", "rename source", "edit source credentials", "rotate API key", "remove source", "disable source", or invokes /source-manage.
---

# Source Manage

Mechanism only. Drives the `lurii-finance` MCP source CRUD tools through a discover → confirm → write loop. **Never write without an explicit confirmation. Never log credential values back to the user. Cascade delete requires a second confirmation.**

**Requires `pfm-mcp` >= 0.23.0** (source CRUD MCP tools `get_source_schema`, `add_source`, `update_source`, `delete_source` plus the existing `list_sources`, `get_collect_status`, `trigger_collect`). On older builds the tool calls in Step 1 / Step 2 will fail with "Unknown tool" — halt and instruct the user to upgrade `lurii-pfm`.

## Hard rules

1. **Never write without confirming.** Every mutating call (`add_source`, `update_source`, `delete_source`) is preceded by an `AskUserQuestion` showing the exact change.
2. **Never echo credential values back.** When confirming `add_source` / `update_source`, show field *names* and a masked indicator (`set` / `unchanged` / `cleared`), not the values themselves. The MCP returns `id`/`name`/`type`/`enabled` only — no secrets.
3. **Type is immutable.** `update_source` does not change `type`. If the user wants to change type, walk them through delete + add.
4. **Cash source is a singleton.** Adding a second `cash` source fails. Surface the existing cash source name from the error.
5. **Cascade delete is destructive.** Default `delete_source` refuses if the source has tx/snap rows. Only set `cascade=true` after a second `AskUserQuestion` showing the row counts.
6. **Don't write to memory.** Source state lives in the MCP DB, not in workspace `memory/`.
7. **Schema-driven cred entry.** Always call `get_source_schema(source_type=...)` first; iterate the returned `fields` list. Don't hardcode field names.
8. **No connection validation here.** This skill writes the source row; verifying credentials is the daemon's job (auto-collect kicks off after `add_source`). If the user wants a pre-flight check, point them at `pfm refresh --source <name>` after adding.

## Step 0 — Resolve intent

Single `AskUserQuestion` to pick the action:

- `add` — new source
- `edit` — rename, rotate creds, toggle enabled
- `delete` — remove a source (with optional cascade)
- `list` — show what's configured (read-only, then re-prompt)
- `cancel` — exit, no write

Free-text "Other" lands here too — re-route to one of the four above.

## Step 1 — Always show current sources first

Before any add/edit/delete branch, call `mcp__lurii-finance__list_sources` and render a compact table the user can refer to:

```
id  name              type            enabled  tx  snap
 1  wise-main         wise            yes      42  120
 2  okx-main          okx             yes     180  300
 3  cash              cash            yes       0   60
```

For `add`: this confirms the user isn't about to create a duplicate name. For `edit`/`delete`: the picker uses the name shown in this table.

## Step 2 — Branches

### 2A. Add

1. Ask for the **source type**. Call `mcp__lurii-finance__get_source_schema` (no arg) to get the full type map. There are ~21 supported types — too many for an `AskUserQuestion` picker (it caps at 4 options). Render the returned type names inline as a code block first, e.g.:
   ```
   Supported types: okx, binance, binance_th, bybit, bunq, cash, coinex, mexc,
   mexc_earn, bitget_wallet, lobstr, blend, wise, kbank, ibkr, rabby, revolut,
   trading212, yo, emcd, generic
   ```
   Then a single `AskUserQuestion`: if the user's original request mentioned a type (e.g. "add a wise source"), offer it as a 2-option picker (`<hint>` / `cancel`) and let the free-text "Other" carry any other choice. If no hint, skip the picker and ask for the type as free text directly. Validate the picked value against the schema's keys; on mismatch, surface `valid_types` from a follow-up `get_source_schema(source_type=<picked>)` error.
2. Call `get_source_schema(source_type=<picked>)` to get `fields`. Each field: `name`, `prompt`, `required`, `default`, `secret`, `tip`.
3. Ask for the **instance name** (free text). Default suggestion: the type name itself if no name conflict, else `<type>-<n>`. Reject blank, duplicate.
4. For each field in order, prompt the user once (free text). For `secret=true`, instruct the user to paste — do NOT echo back. For `required=false`, allow skip → drop key from the dict.
5. Build a confirmation summary:
   ```
   Add source:
     name: wise-eu
     type: wise
     credentials: api_token (set)
   Auto-refresh after add: yes
   ```
6. `AskUserQuestion`: `add` / `cancel`. On `add`, call `add_source(name, source_type, credentials)`.
7. Surface the response. If `auto_refresh.collect == "started"`: tell the user to give it a minute and check `get_collect_status`. If `skipped`, branch on the exact `reason` string returned by the MCP:
   - `"daemon unreachable"` — daemon is not running; source row is committed but no collect happened.
   - `"another collection is running"` — collector is busy; will pick up next cycle.
   - `"source disabled"` — `enabled=False` blocks auto-collect; flip via `update_source(name, enabled=True)`.
   - `"daemon error: <msg>"` — surface verbatim; transient.

   In every `skipped` case instruct `pfm refresh --source <name>` if the user wants an immediate fetch.

### 2B. Edit

1. `AskUserQuestion` to pick the source name from Step 1's table (default: `cancel`).
2. `AskUserQuestion` to pick what to change:
   - `rename` — new name only
   - `rotate credentials` — re-enter one or more cred fields
   - `toggle enabled` — flip the bool
   - `multiple` — combine
   - `cancel`
3. **Rename:** ask new name, validate non-empty + non-duplicate against Step 1's list. Show diff `old → new`.
4. **Rotate credentials:** call `get_source_schema(source_type=<row.type>)`. List the field names; let the user pick which to update via `AskUserQuestion` (multi-step). For each picked field, prompt for the new value. Build a partial `credentials` dict — only changed keys. Unstated fields are merged-preserved by the MCP, **not zeroed**.
5. **Toggle enabled:** show current value, confirm flip.
6. Build a confirmation summary using *names only* for credential fields:
   ```
   Update wise-main:
     new_name: wise-eu
     credentials: api_token (changed)
     enabled: unchanged
   ```
7. `AskUserQuestion`: `update` / `cancel`. On `update`, call `update_source(name, new_name=..., credentials=..., enabled=...)`. Pass only the keys the user changed; omit the rest.
8. Surface the response. Note that credential rotation does NOT trigger a collect — point at `pfm refresh --source <new_name>` if the user wants to verify the new key works.

### 2C. Delete

1. `AskUserQuestion` to pick the name. Show the row's `tx` and `snap` counts inline.
2. Build a first confirmation:
   ```
   Delete source 'okx-main'?
     180 transaction(s), 300 snapshot(s) attached.
     Default delete refuses if data is present.
   ```
3. `AskUserQuestion`:
   - `delete (refuse if data present)` — non-cascade attempt
   - `delete + cascade (also wipe 180 tx, 300 snap)` — destructive
   - `cancel`
4. Non-cascade path: call `delete_source(name)`. If error mentions `cascade=true`, surface the message + counts and re-ask whether to escalate.
5. Cascade path: **second confirmation** — explicit "type the source name to confirm" via `AskUserQuestion` free-text. Trim whitespace on the typed value; compare **case-sensitive** against the source's stored `name` (names are stored as-entered in the DB). On mismatch, halt with `Name mismatch — aborted, no rows touched.` Then call `delete_source(name, cascade=True)`.
6. Surface the `removed` block: snapshots / transactions / analytics_metrics / apy_rules counts.

### 2D. List

Render Step 1's table and re-loop to Step 0 for the next action. No write.

## Failure-mode reference

See `references/error-envelopes.md` for the full error envelope table (daemon unreachable, duplicate cash source, rename collision, missing required field, unknown source type, cascade-refused). Each entry maps a returned `error` string to the recovery step.

## Failure modes to avoid

- **Don't write secret values to the chat.** Show field names + `(set)` / `(changed)` / `(cleared)` only. Never paste an api_key back into the conversation, even when confirming.
- **Don't auto-cascade.** A single user "yes" is not enough for `cascade=true` — require the type-the-name confirmation.
- **Don't try to validate credentials yourself.** That's the collector's job. The skill writes the row and reports the auto-refresh status; the user re-runs `pfm refresh` if they want a hard verify.
- **Don't combine cred update with type change.** `update_source` cannot change `type`. Tell the user to delete + add.
- **Don't rename through the DB.** Use `update_source(new_name=...)` — historical tx/snap stay linked via FK.
- **Don't blanket-zero credentials.** A partial `credentials={"api_key": "new"}` only changes that one key; the rest are preserved by the MCP merge.
