---
name: memory-curator
description: Curate the `memory/` folder when the user shares updates about profile, allocation targets, platforms, principles, or on-horizon items. Edits both YAML frontmatter (canonical for skill consumption) and the markdown body (human prose). Use when the user says "update memory", "remember X", "target changed", "I sold/bought Z", "new platform", "mark Y as executed", invokes /memory-update, or otherwise asks to record, correct, or retire context that belongs in `memory/`. Also use when you (Claude) detect a correction worth persisting across sessions.
---

# Memory Curator

Maintain the `memory/` folder at the repo root. Each file has two layers: **YAML frontmatter** (canonical for skill consumption) and **markdown body** (human prose). Frontmatter is the source of truth — body may lag. Minimal diffs, explicit confirmations on risky edits, append to `memory/CHANGELOG.md` on every change. Honor the schema in `memory/README.md`.

## Files under management

| File | Scope |
|------|-------|
| `memory/profile.md` | Who the investor is: location, goals, horizon, risk, cash flow, portfolio scale, cadence |
| `memory/targets.md` | Allocation targets and deployment priority |
| `memory/platforms.md` | Brokers, exchanges, yield venues, wallets, regional blocks |
| `memory/patterns.md` | Investment principles, MCP data quirks, analysis patterns, style preferences |
| `memory/on-horizon.md` | Active plans and pending actions |
| `memory/CHANGELOG.md` | Dated log of every curator action |

## Route by intent

Classify the user's update, then pick the target file:

- Cash flow / income / expenses / buffer / horizon / risk profile → `profile.md`
- Target % change / new target / priority reorder / rebalance cadence → `targets.md`
- New / removed / blocked platform / rate change / wallet / bridge → `platforms.md`
- New principle / data quirk / style preference / correction to an existing rule → `patterns.md`
- Plan added / item executed / item dropped / progress update → `on-horizon.md`

If unclear, ask the user which file (or which of several to update).

## Edit rules

### Minimal diffs

- Use `Edit` tool, not `Write`. Preserve surrounding content.
- Do not reorder or reformat unrelated sections.
- Keep the file's existing heading and table structure.

### Confirm-before-write — required for

- **Deletes** — removing any frontmatter key, list item, table row, or section
- **Target changes** — any numeric change in `targets.md` (`weight_pct`, `range_pct`, `gap_thresholds.*`)
- **Retiring a principle** — removing or rewording an entry in `patterns.principles[]`
- **Blocked-platform change** — adding to or removing from `platforms.blocked[]`
- **Schema-breaking edits** — removing a required field listed in `memory/README.md`

For these, show the exact diff and ask "Confirm?" before applying.

### Direct write — no confirmation needed for

- Appending a new fact, platform, principle, or horizon item
- Non-destructive adjustments (updating a rate from 13% → 15%, revising a status note, fixing a typo)
- Adding a CHANGELOG entry

### Always

- Update the file timestamp implicit via git/filesystem is enough — do not add timestamps inside files except in `CHANGELOG.md`.
- If a fact contradicts memory, flag the contradiction before writing.
- If the user gives a vague number ("a bit less", "roughly higher"), ask for the exact number — do not invent.

## Horizon transitions

`on-horizon.md` items have three lifecycle states:

- **Active** — currently planned (default)
- **Executed** — completed. Remove from `on-horizon.md`; add CHANGELOG entry with date + detail
- **Dropped** — abandoned. Remove from `on-horizon.md`; CHANGELOG entry with reason

Detect automatic transitions when possible: if the user mentions executing a rec (e.g. "sold <ticker>" or "deployed <amount>"), propose the transition.

## CHANGELOG format

Append to `memory/CHANGELOG.md`. Newest entries at top. Each entry:

```markdown
## YYYY-MM-DD

- **{file.md} — {field or section}:** {one-line description of change}. {Optional rationale.}
```

Group multiple edits from a single session under the same date heading.

Examples (illustrative only — concrete values come from the user's actual memory):

```markdown
## YYYY-MM-DD

- **targets.md — targets[<asset>].weight_pct:** <old>% → <new>% (rationale).
- **on-horizon.md — items[<id>].status:** active → executed; <executed-quantity/value>.
- **platforms.md — yield_venues[<venue>].apy_estimate:** <old>% → <new>% (rate cycle change).
```

## Workflow

1. Parse user intent → route to file.
2. Read the target file.
3. Compose the edit (minimal diff).
4. If destructive per rules above → show diff, ask "Confirm?".
5. Apply edit via `Edit`.
6. Append CHANGELOG entry.
7. Echo changed file + section back to user.

## Failure modes to avoid

- **Do not rewrite a whole file** to add a single bullet. Use `Edit`.
- **Do not duplicate** existing facts — scan first, update in place.
- **Do not invent** numbers, dates, or sources.
- **Do not silently delete** — always show the diff and confirm.
- **Do not switch languages.** Honor the file's existing language; if `patterns.output_language` is set, use it for body prose. Tickers, platform names, code identifiers stay in `ticker_language`.
- **Do not touch non-memory files** (src/, tests/, docs/) — outside this skill's scope.
