---
name: portfolio-advisor
description: Produce a ranked, sourced quantitative portfolio report. Reads `memory/` for all user-specific values (tickers, currencies, platforms, thresholds, language). Hands off memory writes to `memory-curator`. Use when the user says "analyze my portfolio", "rebalance", "investment recommendations", "what should I buy", "monthly report", or invokes /portfolio-advisor.
---

# Portfolio Advisor

Mechanism only. Every user-specific value comes from `memory/` frontmatter — never hardcode tickers, currencies, platforms, thresholds, or language. **Read memory first. Honor it. Halt loud on missing fields.**

## Hard rules

1. **Never infer from position deltas.** Always call `get_transactions` with a date filter for claims about recent activity.
2. **Dedup exchanges per `patterns.md data_quirks`.** Apply each quirk's `rule` field. Common pattern: trust `get_allocation by:source` over `get_yield_positions`.
3. **Exclude buffers from investment math.** Subtract every `profile.md buffers[].amount_usd` before computing deployable capital.
4. **Do not refresh data.** Analyze whatever is in the DB; `pfm refresh` is the user's call.
5. **Do not edit `memory/` directly.** All memory writes route through `memory-curator` in Step 9 with a handoff payload.

Style: numbers not adjectives (`"+$340, +1.8 pp"` not `"meaningful increase"`); cite every external claim; output in `patterns.output_language` with tickers/acronyms in `ticker_language`.

## Step 0 — Offer to refresh cash balance

Before doing anything else, ask the user once via `AskUserQuestion` whether to update the manual cash balance. Stale cash skews every gap-analysis number downstream, but most runs do not need it — keep the prompt cheap and default to skip.

Single `AskUserQuestion` call. Question: **Update cash balance before running the report?** Options:

- `skip` — proceed with current cash from the DB. (Default suggestion.)
- `update now` — invoke the `cash-update` skill via the `Skill` tool, wait for it to return, then continue with Step 1.
- `cancel` — exit cleanly, no report.

Branches:

- `skip` → continue.
- `update now` → call `Skill(skill="cash-update")`. After it returns (success, cancel, or halt), continue with Step 1 — do **not** re-prompt. If `cash-update` halted because the cash source is missing or ambiguous, surface its halt message verbatim and stop the advisor too.
- `cancel` → stop. No memory read, no MCP calls, no report.

## Step 1 — Validate memory

Read all five files in parallel. Parse each YAML frontmatter block. Required fields:

- `profile.md`: `base_currency`, `foreign_currencies`, `buffers`, `portfolio_size_usd_range`, `rebalance_cadence`
- `targets.md`: `targets`, `gap_thresholds`, `priority_order`
- `platforms.md`: `stablecoin_yield_venues`, `blocked`
- `patterns.md`: `output_language`, `report_path_template`, `research_windows`, `recommendation_buckets`, `clarification_triggers`, `data_quirks`, `principles`
- `on-horizon.md`: `items`

If any required field is missing or `null`, halt with this exact message format and stop:

> Memory schema incomplete. Missing: `<file>:<field>`, `<file>:<field>`. Run `/memory-update` (memory-curator) to fill, then re-invoke /portfolio-advisor.

Do not default. Do not invent. Halt.

## Step 2 — Load context

After validation, hold the parsed frontmatter in working memory. Also read the most recent prior report at `<patterns.report_path_template with date=*>` — pick the file with the largest date suffix — for the diff section (Step 7b).

## Step 3 — Collect portfolio data

Run in parallel:

1. `mcp__lurii-finance__get_portfolio_summary`
2. `mcp__lurii-finance__get_allocation` with `by: asset`
3. `mcp__lurii-finance__get_allocation` with `by: source`
4. `mcp__lurii-finance__get_allocation` with `by: category`
5. `mcp__lurii-finance__get_yield_positions`
6. `mcp__lurii-finance__get_currency_exposure`
7. `mcp__lurii-finance__get_risk_metrics`
8. `mcp__lurii-finance__get_pnl`
9. `mcp__lurii-finance__get_transactions` (last 30 days)

Skip `get_snapshots` unless explicit multi-month trend is needed (500-record truncation per `data_quirks.snapshot_truncate_500`).

## Step 4 — Gap analysis (deterministic, memory-driven)

For each entry in `targets.targets[]`, compute current vs target:

- Resolve `asset` against `get_allocation by:asset`. Report `current_pct`, `gap_pp = weight_pct - current_pct`, and `$ shortfall at current price`.
- If `direction: increase` and `gap_pp > 0` → flag for deployment.
- If `direction: trim` and `gap_pp < 0` → flag for trimming.

Apply `targets.gap_thresholds`:

- For each currency in `profile.foreign_currencies`, compute its share of total. If any exceeds `gap_thresholds.idle_cash_pct` (excluding buffers), flag.
- Compute single-largest-holding %. If `gap_thresholds.single_holding_max_pct` is set and exceeded, flag.
- Compute HHI. If `gap_thresholds.hhi_warn` is set and exceeded, flag.
- For each `platforms.yield_venues[].custodial_risk == high`, sum its share. If exceeds `gap_thresholds.custodial_concentration_pct`, flag.

Apply `targets.overlap_groups[]`:

- For each group, list current positions in `tickers[]`. Note non-zero positions outside `consolidation_target` as candidates for the consolidation plan in `on-horizon.md` (do not fabricate sells — defer to horizon items).

Yield rates: per `platforms.stablecoin_yield_venues`, list current APY by asset. Rank. Flag rotation candidates if Δ APY ≥ 2 pp between any two accessible venues.

## Step 5 — External research

Use `WebSearch`; pull full content with `WebFetch` when snippets are insufficient. Aim for 3+ independent sources per theme; vary query phrasing.

For each key in `patterns.research_windows`, run searches across the listed `keywords[]` over `days` lookback:

- `macro`, `equities`, `crypto`, `fx`, `yield` are the canonical buckets — but iterate whatever keys the memory file declares.
- For `equities.keywords` containing `top-5 holdings`, resolve to actual top-5 from `get_allocation by:asset` and search per ticker.
- For `fx.keywords` containing pairs (e.g. `<ccy>/<base>` — actual pairs come from memory), iterate; if `profile.foreign_currencies` includes a currency without a listed pair, add `<ccy>/<base_currency>` to the search set.
- For `yield.keywords`, run a spot check on each `platforms.stablecoin_yield_venues` venue's current rate vs the DB.

Store every source URL with its section.

## Step 6 — Clarify with the user (conditional)

After Step 5, walk through `patterns.clarification_triggers[]`. For each triggered condition, queue a question. Batch all questions into a **single** `AskUserQuestion` call. If no triggers fire, skip silently.

Standard triggers (driven by memory, not hardcoded here):

- The trigger `description` is the user-facing wording (translate to `output_language` if needed).
- Each question must be concise, numeric in the prompt, multiple-choice with sensible defaults plus an "other" free-text option, and independent of other questions in the batch.
- Specifically, for `horizon_decision_pending`: enumerate items from `on-horizon.items[]` where `decision_pending: true`. Ask one question per such item, batched in the same call.

Use the answers to:

- Reword the snapshot anomaly note with the confirmed cause.
- Bias rec ranking, sizing, timing.
- Flag any prior recommendation the user reports as executed (Step 9 handoff input).

## Step 7 — Synthesize

### 7a. Recommendations (ranked, quantitative)

Build recs grouped by `patterns.recommendation_buckets[]`, ordered by `priority`. For each bucket:

- Resolve the bucket id to actionable suggestions using portfolio data + research + horizon items.
- Each rec includes: rationale (1–2 sentences with numbers), expected $ / pp impact, execution note (which platform — must not be in `platforms.blocked[]`), source link(s).
- Cap each bucket at 1–3 recs unless data demands more.

Bucket-resolution hints (driven by memory, not hardcoded):

- `foreign_cash_deployment`: deploy idle foreign-currency cash toward the largest open `direction: increase` target gaps in priority order (`targets.priority_order`).
- `pending_sells`: source from `on-horizon.items[]` with executable next-steps and from `targets.overlap_groups[]` non-canonical positions.
- `stablecoin_rotation`: across `platforms.stablecoin_yield_venues`, recommend moves with Δ APY ≥ 2 pp; cite venue lockup_days.
- `opportunistic_stocks`: 1–2 picks if Step 5 surfaces a clear thesis. Skip otherwise.
- `risk_adjustments`: triggered by Step 4 flags (custodial concentration, single-holding cap, HHI).

### 7b. Diff from prior report (conditional)

Compare to the most recent prior report. Include the diff section only if at least one of: allocation shift > 1 pp in any asset or category; position opened or zeroed; a prior rec executed (detected via transactions). Otherwise omit.

## Step 8 — Output

Write the report to the path resolved from `patterns.report_path_template` with `{date}` = today (`YYYY-MM-DD`). Create parent dirs if missing.

Render per `references/report-template.md` (full section order + headings template). Translate headings to `output_language`; keep tickers/platforms in `ticker_language`.

## Step 9 — Persist & hand off to memory-curator

After writing the report:

1. Branch on `patterns.report_artifact_format`:
   - `cowork` — render the markdown as a self-contained HTML artifact per `references/cowork-html-style.md` and call `mcp__cowork__create_artifact` (or `update_artifact` on id collision).
   - `inline` — return the markdown directly in chat.
   - `none` — skip artifact rendering.

2. Return to chat: one-paragraph summary in `output_language` + path to the new report file.

3. **Hand off to `memory-curator` via the Skill tool** with a handoff brief covering:

   - **Executed items** detected from `get_transactions` since the prior report — which prior-report recommendations are now done, with $ amounts and dates.
   - **New facts to persist** from Step 6 clarification answers.
   - **Status changes** to horizon items.
   - **Corrections** to existing memory contradicted by today's data.

   Memory-curator owns all `Edit` calls, confirmation prompts, and CHANGELOG entries.

## Failure modes to avoid

- **Don't default a missing memory field.** Halt with the Step 1 message.
- **Don't confuse buffers with investment.** Subtract every `profile.buffers[].amount_usd` from deployable capital.
- **Don't recommend a venue in `platforms.blocked[]`.** Filter every rec target against this list.
- **Don't double-count yield.** Apply `data_quirks` rules — typically `get_allocation by:source` is canonical.
- **Don't skip sources.** Every macro / news / yield claim needs a URL; drop the claim if no source.
- **Don't fabricate figures.** "n/a" beats invented data.
- **Don't write in any language other than `output_language`.** Tickers, platform names, acronyms (FX, DTE, IV, HHI, APY), and code stay as-is.
- **Don't skip the clarify step when triggers fire.** Fabricating a cause for an anomaly is a hard violation.
- **Don't edit `memory/` files from inside the advisor.** Even small fixes route through memory-curator in Step 9.
