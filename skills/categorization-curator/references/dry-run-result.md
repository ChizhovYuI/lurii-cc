# Dry-run result schema

`dry_run_category_rule` and `dry_run_type_rule` return the same shape. Surface these fields when reviewing a candidate rule with the user:

| Field | Meaning |
|-------|---------|
| `matched` | Count of transactions the pattern matches in isolation. Tests pattern correctness. |
| `changed[]` | Transactions whose category/type would actually change under priority. First 3: `tx_id`, `proposed_category` / `proposed_type`. |
| `unchanged[]` | Transactions matched but already correct. First 3 — sanity check. No-op for these is fine. |
| `shadowed_by_higher[]` | Transactions the candidate matches but loses to a higher-precedence rule. First 3 + total count. Each entry: `winning_rule_id`, `winning_priority`, `winning_category` / `winning_type`. |
| `overlapping_rules[]` | **Full list** of existing rules that match overlapping transactions. Per entry: rule id, field, value, current result, priority. |
| `raw_field_samples[]` | First 3 raw values seen on the matched rows. |

Validation errors come back as `{"error": "validation", "message": ...}` instead of raising.

## Reading the result

- `matched == 0` → pattern is wrong. Re-inspect raw values.
- `changed == []` but `shadowed_by_higher` non-empty → candidate priority too low (numerically too high). Raise precedence (lower number) or drop.
- `overlapping_rules` non-empty → note "rule X already covers Y of these matches with result Z". Decide: skip new rule, create with higher priority, or create + delete duplicate after.

## Compact mode

For wide-net rules likely to produce >50 entries, pass `summary_only: true`. List buckets become `{count, sample}` (sample = first 5).
