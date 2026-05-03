# Block field tables

For each row, ask one `AskUserQuestion` with options sourced from the listed template path under `templates/<archetype>.yaml`. `parse to [min, max]` means the user picks a range option that maps to a numeric tuple; "Other" lets them enter exact values.

## Block A — `profile.md`

| Field | Template path |
|-------|---------------|
| `region` | `profile.region_options` |
| `goal` | `profile.goal_options` |
| `horizon_years` | `profile.horizon_options` (parse to `[min, max]`) |
| `risk_tolerance` | `profile.risk_options` |
| `experience_years` | `profile.experience_options` (parse to `[min, max]`) |
| `base_currency` | offer the template default + free text |
| `foreign_currencies` | multiSelect from `profile.foreign_currencies_examples` + Other |
| `income_monthly_usd` | `profile.income_monthly_usd_options` |
| `invest_monthly_usd` | `profile.invest_monthly_usd_options` |
| `expenses_monthly_usd_range` | `profile.expenses_monthly_usd_options` (parse to `[min, max]`) |
| `buffers` | iterate: ask buffer name + `profile.buffer_amount_options` for each; allow add-another |
| `portfolio_size_usd_range` | `profile.portfolio_size_usd_options` (parse to `[min, max]`) |
| `rebalance_cadence` | `profile.rebalance_cadence_options` |

## Block B — `targets.md`

1. Ask: **Use the template's suggested targets, customize them, or build from scratch?** (3 options).
2. `use` → adopt `targets.template_targets` verbatim.
3. `customize` → present each template target; keep / adjust / drop. New entries pull from `targets.asset_options`.
4. `scratch` → loop: pick asset from `targets.asset_options`, ask `weight_pct`, `range_pct`, `direction` (`increase | trim | hold`).
5. `gap_thresholds.idle_cash_pct` — `targets.idle_cash_pct_options`.
6. `gap_thresholds.custodial_concentration_pct` — `targets.custodial_concentration_pct_options`.
7. `gap_thresholds.single_holding_max_pct` and `hhi_warn` — free numeric or skip (write `null`).
8. `overlap_groups` — show `targets.example_overlap_groups`; user accepts, edits, or skips.
9. `priority_order` — derived from chosen targets; ask the user to rank via successive multi-choice picks ("which goes first?").

## Block C — `platforms.md`

| Field | Template path |
|-------|---------------|
| `brokers` | multiSelect `platforms.brokers_options`; for each, ask `role` (free text) |
| `crypto_exchanges` | multiSelect `platforms.crypto_exchanges_options` |
| `stablecoin_yield_venues` | subset of crypto_exchanges + `platforms.stablecoin_yield_options` |
| `options_venue` | `platforms.options_venue_options` |
| `wallets` | multiSelect `platforms.wallets_options` |
| `bridges` | free text or skip |
| `blocked` | "any platforms blocked in your region?" — free entries with `name`, `scope`, `reason`, `since` |
| `yield_venues` | for each chosen yield venue, ask `apy_estimate`, `lockup_days`, `custodial_risk` (`platforms.custodial_concern_default` as suggested default) |

## Block D — `patterns.md`

| Field | Template path |
|-------|---------------|
| `output_language` | `patterns.output_language_options` |
| `ticker_language` | offer `en` and `original` |
| `output_format` | `patterns.output_format_options` |
| `report_path_template` | offer `reports/advisor-{date}.md` as default + free text |
| `report_artifact_format` | options: `cowork`, `inline`, `none` |
| `research_windows` | adopt `patterns.research_window_defaults`; ask whether to override `days` per bucket |
| `recommendation_buckets` | offer default ordered list (`foreign_cash_deployment`, `pending_sells`, `stablecoin_rotation`, `opportunistic_stocks`, `risk_adjustments`); keep / reorder / drop |
| `clarification_triggers` | offer the catalog from `references/clarification-triggers.md`; user picks subset |
| `principles` | start from `patterns.default_principles`; user accepts, edits, or adds |
| `data_quirks` | start empty unless the user names known quirks |

After this block, switch all subsequent option labels and confirmation prompts to the chosen `output_language`.

## Block E — `on-horizon.md`

1. multiSelect `on_horizon.active_plan_options` — pick active plans.
2. For each pick, free-text `next_step` and (optional) `decision_pending: true|false`.
3. New `id` slugs auto-generated from titles.
