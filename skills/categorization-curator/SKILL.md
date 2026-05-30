---
name: categorization-curator
description: Iterate on type/category rules via lurii-finance MCP — fix `unknown` types, fill missing categories, dedup rules, link cross-source transfers. Always dry-runs before create; confirms destructive deletes; never writes SQL directly. Use when the user says "categorize", "fix unknowns", "audit categories", "rule cleanup", "dedup rules", "link transfer", or invokes /categorize.
---

# Categorization Curator

Drive the type/category rule loop end-to-end through the lurii-finance MCP. Discover the backlog, propose rules, dry-run them, confirm with the user, create, then batch-apply. Never write SQL directly. **Dry-run before every create. Confirm before every delete.**

## Hard rules

1. **Dry-run before create.** Every `create_*_rule` is preceded by `dry_run_*_rule` with the same args — same source filter (`source_type` XOR `source_id`) and the same `priority`. Surface result per `references/dry-run-result.md`. If `matched == 0`, stop. If `changed == []` but `shadowed_by_higher` non-empty, raise precedence (lower the number) or drop.
2. **Confirm destructive deletes.** Before `delete_*_rule`, dry-run the rule's args and show its current match set + result. Wait for explicit "yes". For bulk deletes, collect candidates into a numbered list with each rule's args, ask for one batch confirmation ("all", "1, 3, 5", "none"), then call `bulk_delete_*_rules`. Always echo args in chat before deletion as a recovery path.
3. **Apply explicitly.** `apply_categorization` is never implicit. Batch several rule edits per apply call.
4. **Manual override is last resort.** `set_transaction_category` is for one-off rows whose pattern doesn't generalize. If two rows share the same raw field, write a rule instead.
5. **No new rule overlaps an existing one without intent.** Read `dry_run.overlapping_rules` per `references/dry-run-result.md`. If overlap is intentional (replacement), schedule the delete after the new rule lands.

Style: narrative in `memory/patterns.md output_language`; tool names, regex patterns, category values, and source names stay in `ticker_language` (default English). If `output_language` is unset, ask once and persist via `memory-curator`.

## Step 1 — Survey

Run in parallel:

1. `mcp__lurii-finance__categorization_summary` (no args) — per-source counts: `total`, `unknown_type`, `no_category`, `internal_transfer`, and the split `transfer_linked` / `transfer_unpaired` (flagged but not yet linked = real transfer work remaining; drives the transfer-linking sub-flow).
2. `mcp__lurii-finance__list_sources` (no args) — `(id, name, type, enabled, tx_count, snap_count)` per configured account. Surfaces the `source_id` values needed when an account-specific rule is in scope.
3. `mcp__lurii-finance__list_categories` (no args) — valid category values per `tx_type`.
4. `mcp__lurii-finance__get_rule_suggestions` with `min_evidence: 2` — patterns the user has manually confirmed via prior `set_transaction_category` calls. Server-side filtering already drops non-discriminating suggestions (same `(source_type, field, value)` mapping to >1 category). Pass `include_non_discriminating: true` only when auditing why a suspected pattern is missing — output then carries `non_discriminating: true` + `conflicting_categories: [...]`.

Pick the highest-pain source by `unknown_type + no_category`. If the user named a source, use that.

Surface the survey in chat as a compact table (header labels translate to `output_language`; source ids and counts stay verbatim):

```
<header-row in output_language: source | total | unknown | no_category | transfer_unpaired>
<source-id-1>  | <total>  | <n>  | <n>  | <n>
<source-id-2>  | <total>  | <n>  | <n>  | <n>
...
```

## Step 2 — Discover

For the chosen source. Source-filter semantics (`source_type` vs `source_id` XOR pair) live in `references/source-filter-adr030.md` — apply when authoring rule args.

- **Survey pass** (cheap): `mcp__lurii-finance__list_uncategorized_transactions` with `source: <src>`, `missing_type: false`, `missing_category: false`, `limit: 100`. Default response is `raw_keys` only — sufficient to spot which fields exist across the backlog. ~10× smaller payload than including samples.
- **Discovery pass** (when patterns need real values): re-call with `include_raw_sample: true` and a narrower `limit` (e.g. 30–50). Returns `raw_sample` (each value truncated to 200 chars) for pattern authoring.
- For ambiguous rows, `mcp__lurii-finance__get_transaction_detail` with the integer row `id` to see full `raw_json`, `winning_category_rule` (id, priority, field, value, result_category), and `winning_type_rule` (same shape on the type side). Either may be `null` — `winning_type_rule` is `null` when the source already supplies a concrete type and no rule fires. Use this to answer "why is this tx X" without iterating through rules.
- **Any row, not just the backlog**: `mcp__lurii-finance__list_transactions` reaches every transaction — already-categorized rows and transfers included — each with its integer `id` and the transfer/category overlay (`category`, `category_source`, `is_internal_transfer`, `transfer_pair_id`, `transfer_detected_by`). Filters: `source`/`source_name`, `tx_type`, `category`, `start`/`end`, `search`, `is_internal_transfer`, `has_pair`, `limit`/`offset`; returns `{count, total, offset, limit, transactions}`. Use it for transfer linking, audits, and fixing already-categorized rows (`list_uncategorized_transactions` only returns the missing-type/category backlog).

Group rows by `raw_keys` (and `raw_sample` on the discovery pass). Look for stable discriminators:

- A field that's the same across many rows (e.g. `kind == "purchase"`) → `eq` rule on that field.
- A field that starts with the same token (e.g. `description` begins with `FX `) → `regex` with `^FX\b`.
- A field that contains a free-form substring → `contains`.
- A normalized merchant token → use the virtual field `merchant_name` (derived per-source: kbank strips the volatile `Ref Xxxx` prefix and embedded ref codes from `details` to reveal the merchant; wise uses `merchant`/`payeeName`; crypto sources yield none). Prefer it over the payment-rail field (e.g. kbank `channel`, which spans dining/groceries/top-ups and produces non-discriminating suggestions). `get_rule_suggestions` already biases toward a discriminating `merchant_name`; author the rule with `field_name: "merchant_name"`.

## Step 3 — Propose & dry-run

For each candidate pattern:

1. Decide field + operator + value.
   - `regex` for anchored / grouped patterns.
   - `contains` for substring.
   - `eq` for exact equality.
2. **For regex rules only:** call `mcp__lurii-finance__validate_rule_args` with `field_operator: "regex"` and `field_value: <pattern>` first. Cheap compile-only check (no DB scan). On `valid: false`, fix the pattern before paying for the dry-run query.
3. Call `mcp__lurii-finance__dry_run_category_rule` (or `dry_run_type_rule`) with the same args you would pass to `create_*_rule`, plus `scope_source` if source-specific, plus `limit: 200`. For wide-net rules likely to produce >50 entries, pass `summary_only: true`.
4. Surface the dry-run result + interpret per `references/dry-run-result.md` (full field map, threshold rules, overlap protocol).

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

Three conditional branches off the main loop — load `references/sub-flows.md` when the trigger fires:

- **Manual override** — user says "this one transaction is wrong" → `set_transaction_category` on a single row.
- **Transfer linking** — `categorization_summary.transfer_unpaired > 0`, or user asks to link/unlink → `suggest_transfer_links` → `bulk_link_transfers`; `repair_transfer_pairs` to fix asymmetric links.
- **Rule cleanup pass** — user says "audit rules" / "dedup" → `audit_*_rules` survey + bulk-confirm deletes.

## Failure modes to avoid

- **Don't create a rule on `matched == 0`.** Pattern is wrong. Stop and re-inspect raw values.
- **Don't delete a rule whose dry-run still matches without a replacement.** Find the replacement first.
- **Don't fabricate categories.** Cite `list_categories(tx_type)`. If the user wants a new category, point them to the SwiftUI app or a direct `MetadataStore.add_category` call (out of skill scope).
- **Don't `apply_categorization` per rule.** The bulk pass itself is fast (~1k rows is essentially instant); the rule is about *not* hiding cost in iteration, not about avoiding apply. Batch several rule edits per apply call instead.
- **Don't infer raw field meaning.** If you can't tell what `raw_json` field X represents, call `get_transaction_detail` and ask the user.
- **Don't `contains` a pattern that needs anchoring.** "FX" as substring also matches "TAXFX1234". Use `^FX\b` instead.
- **Don't mix `tx_id` (string) with `id` (integer).** Listing tools (`list_transactions`, `list_uncategorized_transactions`) return both. Mutation tools (`set_transaction_category`, `link_transfer`, `bulk_link_transfers`, `unlink_transfer`) take the integer `id`. Every row — categorized or transfer — is reachable by `id` via `list_transactions`; never guess ids.
- **Don't hand-match transfer pairs.** Use `suggest_transfer_links` (server-side asset/amount/date matcher), not manual cross-source eyeballing. Confirm candidates with the user before `bulk_link_transfers`, and treat a `score < 1.0` as a fee/valuation gap to sanity-check.
- **Don't skip dry-run because "the pattern looks obvious".** Overlap detection only happens through `dry_run_*_rule.overlapping_rules`.
- **Don't write narrative in any language other than `memory/patterns.md output_language`.** Tool names, regex patterns, category values, and source names stay in `ticker_language` (default English).
