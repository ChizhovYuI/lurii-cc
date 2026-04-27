---
name: memory-init
description: First-time interactive setup of the `memory/` folder for a new clone or blank install. Picks an investor archetype, asks structured questions with template-driven option lists, and writes five memory files with YAML frontmatter per the schema in `memory/README.md`. Use when `memory/` is missing, empty, or the user invokes /memory-init or asks to "initialize memory", "set up memory", "bootstrap memory".
---

# Memory Init

Interactive onboarding. Mechanism only — option lists come from `templates/<archetype>.yaml`. The skill asks one question per turn, collects answers, then writes five frontmatter-keyed memory files plus the CHANGELOG seed.

## Guard

Read the state of `memory/` first.

- Missing or only `README.md` / `CHANGELOG.md` → proceed.
- Any of `profile.md`, `targets.md`, `platforms.md`, `patterns.md`, `on-horizon.md` already has non-trivial content → halt and confirm with `AskUserQuestion`. Options: `overwrite`, `extend`, `abort`. Default recommendation: **abort** — route to `memory-curator` for incremental updates.

## Tool rules

- One question per turn via `AskUserQuestion`. 2–4 options each. The tool auto-provides "Other" (free text).
- Numeric answers: surface 3 plausible ranges from the template; "Other" lets the user enter exact values.
- Never invent. Skipped fields land as `null` in frontmatter so skills can detect missing config.
- Question wording: terse and structural. Translate option labels to the chosen `output_language` after Block D.

## Step 0 — Pick archetype

Single `AskUserQuestion`. Options are the three archetype files in `templates/`:

- `equity-heavy` — index/ETF investor; equities-first; modest crypto
- `crypto-native` — crypto-first; BTC/ETH core; stablecoin yield
- `mixed` — balanced multi-asset; ETFs + stocks + crypto + yield

Read the chosen `templates/<archetype>.yaml`. All subsequent option lists come from this file.

## Step 1 — Block A: Profile (`profile.md`)

For each field, `AskUserQuestion` with options sourced from the template path noted:

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

## Step 2 — Block B: Targets (`targets.md`)

1. Ask: **Use the template's suggested targets, customize them, or build from scratch?** (3 options)
2. If "use" → adopt `targets.template_targets` verbatim.
3. If "customize" → present each template target and ask whether to keep / adjust / drop. New entries pull from `targets.asset_options`.
4. If "scratch" → loop: pick asset from `targets.asset_options`, ask `weight_pct`, `range_pct`, `direction` (`increase | trim | hold`).
5. `gap_thresholds.idle_cash_pct` — `targets.idle_cash_pct_options`
6. `gap_thresholds.custodial_concentration_pct` — `targets.custodial_concentration_pct_options`
7. `gap_thresholds.single_holding_max_pct` and `hhi_warn` — free numeric or skip (write `null`).
8. `overlap_groups` — show `targets.example_overlap_groups`; user accepts, edits, or skips.
9. `priority_order` — derived from chosen targets; ask the user to drag-equivalent rank via successive multi-choice picks ("which goes first?").

## Step 3 — Block C: Platforms (`platforms.md`)

| Field | Template path |
|-------|---------------|
| `brokers` | multiSelect `platforms.brokers_options`; for each, ask `role` (free text) |
| `crypto_exchanges` | multiSelect `platforms.crypto_exchanges_options` |
| `stablecoin_yield_venues` | subset of crypto_exchanges + `platforms.stablecoin_yield_options` |
| `options_venue` | `platforms.options_venue_options` |
| `wallets` | multiSelect `platforms.wallets_options` |
| `bridges` | free text or skip |
| `blocked` | ask "any platforms blocked in your region?" — free entries with `name`, `scope`, `reason`, `since` |
| `yield_venues` | for each chosen yield venue, ask `apy_estimate`, `lockup_days`, `custodial_risk` (use `platforms.custodial_concern_default` as suggested default) |

## Step 4 — Block D: Patterns (`patterns.md`)

| Field | Template path |
|-------|---------------|
| `output_language` | `patterns.output_language_options` |
| `ticker_language` | offer `en` and `original` |
| `output_format` | `patterns.output_format_options` |
| `report_path_template` | offer `reports/advisor-{date}.md` as default + free text |
| `report_artifact_format` | options: `cowork`, `inline`, `none` |
| `research_windows` | adopt `patterns.research_window_defaults`; ask whether to override `days` per bucket |
| `recommendation_buckets` | offer a default ordered list (`foreign_cash_deployment`, `pending_sells`, `stablecoin_rotation`, `opportunistic_stocks`, `risk_adjustments`); ask the user to keep / reorder / drop |
| `clarification_triggers` | offer a default catalog from this file (see below); user picks subset |
| `principles` | start from `patterns.default_principles`; user accepts, edits, or adds |
| `data_quirks` | start empty unless the user names known quirks for their data sources |

After this block, switch all subsequent option labels and confirmation prompts to the chosen `output_language`.

### Default clarification triggers catalog

Offer these as multiSelect; user keeps the relevant subset:

- `net_worth_delta_5pct` — Net-worth Δ > 5% vs prior report
- `source_ghost_movement` — source-level $ delta unexplained by transactions
- `new_or_zeroed_asset` — asset newly held or dropped to zero with no transaction
- `macro_event_within_7d` — high-impact macro event within 7 days
- `top5_holding_event` — top-5 holding earnings / regulatory / >5% single-day move
- `stale_data` — source > 5% NAV with snapshot age > 7d
- `horizon_decision_pending` — on-horizon item awaiting user decision

## Step 5 — Block E: On-horizon (`on-horizon.md`)

1. multiSelect `on_horizon.active_plan_options` — pick active plans.
2. For each pick, free-text `next_step` and (optional) `decision_pending: true|false`.
3. New `id` slugs auto-generated from titles.

## Step 6 — Review and confirm

1. Show captured answers compactly: one line per top-level field group.
2. `AskUserQuestion` with options: **Write all files / Edit a section / Abort**.
3. On "Edit a section" → re-ask only that section.
4. On "Write all files" → proceed.

## Step 7 — Write

Render YAML frontmatter per the schema in `memory/README.md`, then a markdown body with section headings reflecting the captured fields. Write in this order:

1. `memory/profile.md`
2. `memory/targets.md`
3. `memory/platforms.md`
4. `memory/patterns.md`
5. `memory/on-horizon.md`
6. `memory/README.md` — only if missing
7. `memory/CHANGELOG.md` — seed entry: `## YYYY-MM-DD\n\n- **Initial scaffold:** memory/ created via memory-init using <archetype> archetype.`

## Step 8 — Closeout

Return to chat in the user's chosen `output_language`:

- Confirmation that `memory/` is populated.
- Path list of files written.
- Suggested next step: run `portfolio-advisor` for the first report, or use `memory-curator` to refine.

## Failure modes to avoid

- **Don't skip the guard.** Overwriting non-empty memory destroys curated context.
- **Don't batch questions.** One question per `AskUserQuestion` call.
- **Don't fabricate.** Skipped fields land as `null`.
- **Don't translate user free text.** Preserve exact wording.
- **Don't commit to git.** That is the user's call.
- **Don't bake new archetype-specific values into this file.** New archetypes get a new `templates/<name>.yaml`, not a SKILL.md edit.
