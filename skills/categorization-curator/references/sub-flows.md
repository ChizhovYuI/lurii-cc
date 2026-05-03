# Sub-flows

Conditional flows that branch off the main loop. Load when the user's intent matches.

## Manual override

Trigger: "this one transaction is wrong".

1. Get the integer row id from `list_uncategorized_transactions` or `get_transaction_detail` (the listing surfaces both `id: int` and `tx_id: str` — use `id`).
2. Call `mcp__lurii-finance__set_transaction_category` with `transaction_id` + `category`.
3. The override also records to `user_category_choices`; a future session's `get_rule_suggestions` will surface it. If the same raw pattern appears 2+ times, propose converting the override to a rule.

## Transfer linking

Trigger: `categorization_summary` shows `internal_transfer > 0` but the user identifies a missed cross-source pair, or asks to link/unlink.

- `mcp__lurii-finance__link_transfer` with `tx_id_a` and `tx_id_b` (both integer row ids).
- Reverse: `mcp__lurii-finance__unlink_transfer` with `transaction_id`.

Linked transfers are excluded from spending math by the analytics layer — confirm with the user before unlinking.

## Rule cleanup pass

Trigger: "audit rules" / "dedup".

1. Call `mcp__lurii-finance__audit_category_rules` (and/or `audit_type_rules`). Single call returns:
   - `rules` (sorted by `matched_count` ASC)
   - `dead` (rules with `matched_count == 0` — safe to delete)
   - `shadowed_dead` (match in isolation but lose to higher-precedence — harmless until the upstream rule is removed)
   Pass `scope_source` to scope evaluation to one source's traffic. **Always audit before manual dedup** — it finds dead rules cheaply in one pass.
2. Surface `dead` first: each candidate's args + propose deletion. 100% safe to remove. Use `bulk_delete_*_rules` after batch confirmation.
3. For overlap detection within active rules, `dry_run_category_rule` per rule with that rule's own args; read `overlapping_rules`.
4. Two rules overlap with **same** `result_category` → either is a delete candidate (criterion: clearer description / more accurate field, not just "older id"). Surface the group with all rule args; user picks.
5. Two rules overlap with **different** results → surface the conflict; user decides which to keep.
6. **Batch-confirm.** Collect *all* delete candidates into a numbered list, echo each rule's args (recovery path), one batch confirmation ("all", "1, 3, 5", "none"). Then `bulk_delete_*_rules(rule_ids=[...])`. The tool returns `{"deleted": [...], "not_found": [...]}` — surface both buckets.
7. After all deletes, `apply_categorization(force: true)` once.
