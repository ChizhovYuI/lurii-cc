---
name: categorization-curator
description: Iterate on type and category rules in the lurii-finance MCP database — fix `unknown` types, fill missing categories, dedup overlapping rules, and link missed cross-source transfers. Honors `memory/patterns.md output_language` for narrative. Use when the user says "categorize", "fix unknowns", "audit categories", "rule cleanup", "dedup rules", "link transfer", invokes /categorize, or otherwise asks to triage uncategorized transactions or curate categorization rules. Always dry-run before create. Confirm destructive deletes.
---

# Categorization Curator

Drive the type/category rule loop end-to-end through the lurii-finance MCP. Discover the backlog, propose rules, dry-run them, confirm with the user, create, then batch-apply. Never write SQL directly. **Dry-run before every create. Confirm before every delete.**

## Hard rules

1. **Dry-run before create.** Every `create_*_rule` is preceded by `dry_run_*_rule` with the same args — including the source filter (`source_type` or `source_id`, never both) and `priority` (set explicitly when overriding the default specificity scheme). Show `matched`, sample of `changed`, `len(shadowed_by_higher)`, and `overlapping_rules`. If `matched == 0`, stop — pattern is wrong. If `changed == []` but `shadowed_by_higher` is non-empty, the rule's priority is too low (numerically too high) to win any tx; raise precedence (lower the number) or drop the rule.
2. **Confirm destructive deletes.** Before `delete_*_rule`, dry-run the rule's args and show its current match set + result. Wait for explicit "yes". For **bulk** deletes (cleanup pass with multiple rules), collect candidates into a numbered list with each rule's args and ask for one batch confirmation ("all", "1, 3, 5", "none") — then call `bulk_delete_*_rules` with the chosen ids. Always preserve each rule's args in chat before deletion as a recovery path.
3. **Apply explicitly.** `apply_categorization` is never implicit. Batch several rule edits per apply call.
4. **Regex over `contains` for anchored patterns.** Prefer `^FX\b`, `^(POS|ATM)\b` over `contains:FX`. Use `(?i)` inline flag for case-insensitive — never lossy `lower()`.
5. **Manual override is last resort.** `set_transaction_category` is for one-off rows whose pattern doesn't generalize. If two rows share the same raw field, write a rule instead.
6. **No new rule overlaps an existing one without intent.** Use `dry_run.overlapping_rules` to confirm. If overlap is intentional (replacement), schedule the delete after the new rule lands.
7. **Don't fabricate categories.** Only use values from `list_categories(tx_type)`.
8. **Narrative language follows `memory/patterns.md output_language`.** Tool names, regex patterns, category values, and source names stay in their `ticker_language` form (default English). If `output_language` is unset, ask once and persist via `memory-curator`.

## Step 1 — Survey

Run in parallel:

1. `mcp__lurii-finance__categorization_summary` (no args) — per-source counts: `total`, `unknown_type`, `no_category`, `internal_transfer`.
2. `mcp__lurii-finance__list_sources` (no args) — `(id, name, type, enabled, tx_count, snap_count)` per configured account. Surfaces the `source_id` values needed when an account-specific rule is in scope.
3. `mcp__lurii-finance__list_categories` (no args) — valid category values per `tx_type`.
4. `mcp__lurii-finance__get_rule_suggestions` with `min_evidence: 2` — patterns the user has manually confirmed via prior `set_transaction_category` calls. Server-side filtering already drops non-discriminating suggestions (same `(source_type, field, value)` mapping to >1 category). Pass `include_non_discriminating: true` only when auditing why a suspected pattern is missing — output then carries `non_discriminating: true` + `conflicting_categories: [...]`.

Pick the highest-pain source by `unknown_type + no_category`. If the user named a source, use that.

Surface the survey in chat as a compact table (header labels translate to `output_language`; source ids and counts stay verbatim):

```
<header-row in output_language: source | total | unknown | no_category | transfer>
<source-id-1>  | <total>  | <n>  | <n>  | <n>
<source-id-2>  | <total>  | <n>  | <n>  | <n>
...
```

## Step 2 — Discover

For the chosen source:

**Account vs. type filter (ADR-030 Stage 3).** Rules now use a XOR pair:

- `source_type: "<type>"` — rule applies to **every** transaction of that type (e.g. `source_type: "kbank"` matches any kbank account).
- `source_id: <int>` — rule applies only to that **specific account instance** (use the id from `list_sources`).
- both omitted — catch-all (matches every transaction).

Pick whichever fits the pattern: type for cross-account behavior (e.g. all kbank monthly statements), `source_id` for an account-specific quirk (e.g. one wise account that uses a different `_balance_direction` field).

The legacy `source` parameter is still accepted as a deprecation alias — auto-resolved against `sources` (matches `sources.name` → `source_id`, anything else → `source_type`). Prefer the explicit pair.

Use `mcp__lurii-finance__list_sources` to enumerate `(id, name, type, tx_count, snap_count)` before authoring an instance-pinned rule.

- **Survey pass** (cheap): `mcp__lurii-finance__list_uncategorized_transactions` with `source: <src>`, `missing_type: false`, `missing_category: false`, `limit: 100`. Default response is `raw_keys` only — sufficient to spot which fields exist across the backlog. ~10× smaller payload than including samples.
- **Discovery pass** (when patterns need real values): re-call with `include_raw_sample: true` and a narrower `limit` (e.g. 30–50). Returns `raw_sample` (each value truncated to 200 chars) for pattern authoring.
- For ambiguous rows, `mcp__lurii-finance__get_transaction_detail` with the integer row `id` to see full `raw_json`, `winning_category_rule` (id, priority, field, value, result_category), and `winning_type_rule` (same shape on the type side). Either may be `null` — `winning_type_rule` is `null` when the source already supplies a concrete type and no rule fires. Use this to answer "why is this tx X" without iterating through rules.

Group rows by `raw_keys` (and `raw_sample` on the discovery pass). Look for stable discriminators:

- A field that's the same across many rows (e.g. `kind == "purchase"`) → `eq` rule on that field.
- A field that starts with the same token (e.g. `description` begins with `FX `) → `regex` with `^FX\b`.
- A field that contains a free-form substring → `contains`.

## Step 3 — Propose & dry-run

For each candidate pattern:

1. Decide field + operator + value.
   - `regex` for anchored / grouped patterns.
   - `contains` for substring.
   - `eq` for exact equality.
2. **For regex rules only:** call `mcp__lurii-finance__validate_rule_args` with `field_operator: "regex"` and `field_value: <pattern>` first. Cheap compile-only check (no DB scan). On `valid: false`, fix the pattern before paying for the dry-run query.
3. Call `mcp__lurii-finance__dry_run_category_rule` (or `dry_run_type_rule`) with the same args you would pass to `create_*_rule`, plus `scope_source` if the rule is source-specific, plus `limit: 200`. For catch-all or wide-net rules likely to produce >50 changed/shadowed entries, pass `summary_only: true` — list buckets become `{count, sample}` (sample = first 5) so the response stays compact. Validation errors come back as `{"error": "validation", "message": ...}` instead of raising — surface the message and re-prompt the user.
4. Surface the dry-run result:
   - `matched` count (isolation match — pattern correctness).
   - First 3 of `changed` (`tx_id`, `proposed_category` / `proposed_type`) — real post-priority effect.
   - First 3 of `unchanged` (sanity check — these are already categorized; if they're already correct, the rule is a no-op for them, which is fine).
   - `len(shadowed_by_higher)` + first 3 entries (`winning_rule_id`, `winning_priority`, `winning_category` / `winning_type`) — tx the candidate matches but loses to a higher-precedence existing rule.
   - **Full `overlapping_rules`** (rule id, field, value, current result, priority).
   - First 3 of `raw_field_samples`.

If `matched == 0`: stop. Re-inspect raw values, refine pattern, dry-run again.

If `overlapping_rules` is non-empty: explicitly note "rule X already covers Y of these matches with result Z". Decide together with user whether to (a) skip the new rule, (b) create with higher priority, or (c) create + delete the duplicate after.

## Step 4 — Confirm & create

Wait for user OK. On confirm:

- `mcp__lurii-finance__create_category_rule` (or `create_type_rule`) with the same args used in dry-run (minus `scope_source` and `limit`).
- If the result includes a `ValueError` envelope (malformed regex), surface it and re-prompt.

Track all rule ids created in this session — needed for the optional cleanup pass.

## Step 5 — Apply

When the user signals "ready" (or after batching ~3–5 rule edits):

- `mcp__lurii-finance__apply_categorization` with `force: false`. Surface the result diff: `total`, `type_resolved`, `transfers`, `categorized`.

If the user wants to force a full re-categorize (e.g. after deleting a rule that previously won), pass `force: true` — but warn that it scans the full table.

## Step 6 — Loop or close

Re-call `categorization_summary` for the source. If `(unknown_type + no_category) / total >= 0.05`, loop back to Step 2. Otherwise, hand back to the user with a one-line summary:

```
kbank: unknown 87 → 4, no_category 312 → 18. Created 6 rules. Applied.
```

## Sub-flows

### Manual override

When user says "this one transaction is wrong":

1. Get the integer row id from `list_uncategorized_transactions` or `get_transaction_detail` (the listing surfaces both `id: int` and `tx_id: str` — use `id`).
2. `mcp__lurii-finance__set_transaction_category` with `transaction_id` and `category`.
3. The override also records to `user_category_choices` — a future session's `get_rule_suggestions` will surface it. So if the same raw pattern appears 2+ times, propose converting the override to a rule.

### Transfer linking

When `categorization_summary` shows `internal_transfer > 0` but the user identifies a missed cross-source pair:

- `mcp__lurii-finance__link_transfer` with `tx_id_a` and `tx_id_b` (both integer row ids).
- Reverse: `mcp__lurii-finance__unlink_transfer` with `transaction_id`.

Linked transfers are excluded from spending math by the analytics layer — confirm with the user before unlinking.

### Rule cleanup pass

When user says "audit rules" / "dedup":

1. `mcp__lurii-finance__audit_category_rules` (and/or `audit_type_rules`) — single call returns `rules` (sorted by `matched_count` ASC), `dead` (rules with `matched_count == 0` — safe to delete), and `shadowed_dead` (rules that match in isolation but lose to higher-precedence rules — harmless until something above is removed). Run with `scope_source` to scope evaluation to a single source's traffic. **Always run audit before manual dedup** — finds dead rules cheaply in one pass.
2. Surface `dead` first: each candidate's args + propose deletion. These are 100% safe to remove. Use `bulk_delete_*_rules` after batch confirmation (see hard rule #2).
3. For overlap detection within active rules, `dry_run_category_rule` per rule with that rule's own args, read `overlapping_rules` from the result.
4. If two rules overlap and both produce the **same** `result_category`: either rule is a delete candidate (the criterion is which one has a clearer description / more accurate field choice — not just "older id"). Surface the duplicate group in chat, including each rule's args, and let the user pick.
5. If they overlap but produce **different** results: surface the conflict — user decides which to keep.
6. **Batch-confirm pattern.** Collect *all* delete candidates first into a numbered list, surface them in one message with their args (so the user has a recovery path if they need to reconstruct), and ask for one confirmation covering the batch ("подтверди удаление 1, 3, 5" / "all" / "none"). Then call `mcp__lurii-finance__bulk_delete_category_rules` (or `bulk_delete_type_rules`) with the confirmed `rule_ids`. The bulk tool returns `{"deleted": [...], "not_found": [...]}` — surface both buckets.
7. After all deletes, `apply_categorization(force: true)` once.

## Failure modes to avoid

- **Don't create a rule on `matched == 0`.** Pattern is wrong. Stop and re-inspect raw values.
- **Don't delete a rule whose dry-run still matches without a replacement.** Find the replacement first.
- **Don't fabricate categories.** Cite `list_categories(tx_type)`. If the user wants a new category, point them to the SwiftUI app or a direct `MetadataStore.add_category` call (out of skill scope).
- **Don't `apply_categorization` per rule.** The bulk pass itself is fast (~1k rows is essentially instant); the rule is about *not* hiding cost in iteration, not about avoiding apply. Batch several rule edits per apply call instead.
- **Don't infer raw field meaning.** If you can't tell what `raw_json` field X represents, call `get_transaction_detail` and ask the user.
- **Don't `contains` a pattern that needs anchoring.** "FX" as substring also matches "TAXFX1234". Use `^FX\b` instead.
- **Don't mix `tx_id` (string) with `id` (integer).** Listing tools return both. Mutation tools (`set_transaction_category`, `link_transfer`, `unlink_transfer`) take the integer `id`.
- **Don't skip dry-run because "the pattern looks obvious".** Overlap detection only happens through `dry_run_*_rule.overlapping_rules`.
- **Don't write narrative in any language other than `memory/patterns.md output_language`.** Tool names, regex patterns, category values, and source names stay in `ticker_language` (default English).
