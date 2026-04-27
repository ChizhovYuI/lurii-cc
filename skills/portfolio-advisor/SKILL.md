---
name: portfolio-advisor
description: Analyze the user's portfolio, research global macro / news / yields against their stated targets, and produce a ranked, quantitative investment recommendations report. Reads `memory/` for all user-specific context (currencies, tickers, platforms, thresholds, language, output format). Use when the user asks to "analyze my portfolio", "rebalance", "investment recommendations", "what should I buy", "monthly report", invokes /portfolio-advisor, or otherwise requests a full portfolio review with actionable recs.
---

# Portfolio Advisor

Mechanism only. Every user-specific value comes from `memory/` frontmatter — never hardcode tickers, currencies, platforms, thresholds, or language. **Read memory first. Honor it. Halt loud on missing fields.**

## Hard rules

1. **Never infer from position deltas.** Always call `get_transactions` with a date filter for claims about recent activity.
2. **Dedup exchanges per `patterns.md data_quirks`.** Apply each quirk's `rule` field. Common pattern: trust `get_allocation by:source` over `get_yield_positions`.
3. **Exclude buffers from investment math.** Read `profile.md buffers[]`; subtract `amount_usd` totals before computing deployable capital.
4. **Do not refresh data.** Analyze whatever is in the DB. The user runs `pfm refresh` separately.
5. **Output in `patterns.md output_language`.** Tickers, platform names, and acronyms keep their `ticker_language` form.
6. **Cite everything.** Every external claim (macro, news, yield rate) gets a source URL.
7. **Numbers, not adjectives.** "+$340, +1.8 pp" beats "meaningful increase".
8. **Do not edit `memory/` directly.** All memory writes route through `memory-curator` in Step 8 with a handoff payload.

## Step 0 — Validate memory

Read all five files in parallel. Parse each YAML frontmatter block. Required fields:

- `profile.md`: `base_currency`, `foreign_currencies`, `buffers`, `portfolio_size_usd_range`, `rebalance_cadence`
- `targets.md`: `targets`, `gap_thresholds`, `priority_order`
- `platforms.md`: `stablecoin_yield_venues`, `blocked`
- `patterns.md`: `output_language`, `report_path_template`, `research_windows`, `recommendation_buckets`, `clarification_triggers`, `data_quirks`, `principles`
- `on-horizon.md`: `items`

If any required field is missing or `null`, halt with this exact message format and stop:

> Memory schema incomplete. Missing: `<file>:<field>`, `<file>:<field>`. Run `/memory-update` (memory-curator) to fill, then re-invoke /portfolio-advisor.

Do not default. Do not invent. Halt.

## Step 1 — Load context

After validation, hold the parsed frontmatter in working memory. Also read the most recent prior report at `<patterns.report_path_template with date=*>` — pick the file with the largest date suffix — for the diff section (Step 6b).

## Step 2 — Collect portfolio data

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

## Step 3 — Gap analysis (deterministic, memory-driven)

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

## Step 4 — External research

Use `WebSearch`; pull full content with `WebFetch` when snippets are insufficient. Aim for 3+ independent sources per theme; vary query phrasing.

For each key in `patterns.research_windows`, run searches across the listed `keywords[]` over `days` lookback:

- `macro`, `equities`, `crypto`, `fx`, `yield` are the canonical buckets — but iterate whatever keys the memory file declares.
- For `equities.keywords` containing `top-5 holdings`, resolve to actual top-5 from `get_allocation by:asset` and search per ticker.
- For `fx.keywords` containing pairs (e.g. `<ccy>/<base>` — actual pairs come from memory), iterate; if `profile.foreign_currencies` includes a currency without a listed pair, add `<ccy>/<base_currency>` to the search set.
- For `yield.keywords`, run a spot check on each `platforms.stablecoin_yield_venues` venue's current rate vs the DB.

Store every source URL with its section.

## Step 5 — Clarify with the user (conditional)

After Step 4, walk through `patterns.clarification_triggers[]`. For each triggered condition, queue a question. Batch all questions into a **single** `AskUserQuestion` call. If no triggers fire, skip silently.

Standard triggers (driven by memory, not hardcoded here):

- The trigger `description` is the user-facing wording (translate to `output_language` if needed).
- Each question must be concise, numeric in the prompt, multiple-choice with sensible defaults plus an "other" free-text option, and independent of other questions in the batch.
- Specifically, for `horizon_decision_pending`: enumerate items from `on-horizon.items[]` where `decision_pending: true`. Ask one question per such item, batched in the same call.

Use the answers to:

- Reword the snapshot anomaly note with the confirmed cause.
- Bias rec ranking, sizing, timing.
- Flag any prior recommendation the user reports as executed (Step 8 handoff input).

## Step 6 — Synthesize

### 6a. Recommendations (ranked, quantitative)

Build recs grouped by `patterns.recommendation_buckets[]`, ordered by `priority`. For each bucket:

- Resolve the bucket id to actionable suggestions using portfolio data + research + horizon items.
- Each rec includes: rationale (1–2 sentences with numbers), expected $ / pp impact, execution note (which platform — must not be in `platforms.blocked[]`), source link(s).
- Cap each bucket at 1–3 recs unless data demands more.

Bucket-resolution hints (driven by memory, not hardcoded):

- `foreign_cash_deployment`: deploy idle foreign-currency cash toward the largest open `direction: increase` target gaps in priority order (`targets.priority_order`).
- `pending_sells`: source from `on-horizon.items[]` with executable next-steps and from `targets.overlap_groups[]` non-canonical positions.
- `stablecoin_rotation`: across `platforms.stablecoin_yield_venues`, recommend moves with Δ APY ≥ 2 pp; cite venue lockup_days.
- `opportunistic_stocks`: 1–2 picks if Step 4 surfaces a clear thesis. Skip otherwise.
- `risk_adjustments`: triggered by Step 3 flags (custodial concentration, single-holding cap, HHI).

### 6b. Diff from prior report (conditional)

Compare to the most recent prior report. Include the diff section only if at least one of: allocation shift > 1 pp in any asset or category; position opened or zeroed; a prior rec executed (detected via transactions). Otherwise omit.

## Step 7 — Output

Write the report to the path resolved from `patterns.report_path_template` with `{date}` = today (`YYYY-MM-DD`). Create parent dirs if missing.

Section order (translate headings to `output_language`; keep tickers/platforms in `ticker_language`):

```markdown
# Portfolio report — {{YYYY-MM-DD}}

## Snapshot
- Net worth: $X,XXX
- Allocation by category: ...
- Top-5 positions: ...
- HHI: 0.XX | Concentration: X.X%
- Warnings (stale sources, etc.)

## Macro context
(per `research_windows.macro.days` lookback, 5+ sources)

## Equities
(per `research_windows.equities.days`, top-5 + targets with `direction: increase`)

## Crypto
(per `research_windows.crypto.days`)

## FX
(per `research_windows.fx.days`, pairs derived from `profile.foreign_currencies`)

## Stablecoin yields
(per `research_windows.yield.days`, venues from `platforms.stablecoin_yield_venues`)

## Gaps and risks
(target gaps, foreign-cash %, custodial concentration, overlap groups)

## Recommendations
1. **{{Action}}** — $X, rationale, execution, source
2. ...

## Changes since last report
(only if material — see 6b)

## Sources
Grouped by section.
```

## Step 8 — Persist & hand off to memory-curator

After writing the report:

1. **If `patterns.report_artifact_format == cowork`**, render the markdown as a self-contained HTML artifact and call `mcp__cowork__create_artifact` (or `update_artifact` if id collides) with `id` matching the filename stem. HTML constraints: light color-scheme, white background, system sans-serif, max-width ~820px, padding ~28px 36px. Headings 24/18/15px weight 500. Tables with 1px `#e5e5e5` borders, `#f9f9f9` header. Inline `<code>` for tickers (13px monospace, `#f3f3f3` bg). Links `#2c5cc5`, `target="_blank" rel="noreferrer"`. All CSS inline; no external resources, no JS, no markdown library. Body order matches the .md.
   **If `patterns.report_artifact_format == inline`**, return the markdown directly in chat.
   **If `patterns.report_artifact_format == none`**, skip artifact rendering.

2. Return to chat: one-paragraph summary in `output_language` + path to the new report file.

3. **Hand off to `memory-curator` via the Skill tool** with a handoff brief covering:

   - **Executed items** detected from `get_transactions` since the prior report — which prior-report recommendations are now done, with $ amounts and dates.
   - **New facts to persist** from Step 5 clarification answers.
   - **Status changes** to horizon items.
   - **Corrections** to existing memory contradicted by today's data.

   Memory-curator owns all `Edit` calls, confirmation prompts, and CHANGELOG entries.

## Failure modes to avoid

- **Don't default a missing memory field.** Halt with the Step 0 message.
- **Don't confuse buffers with investment.** Subtract every `profile.buffers[].amount_usd` from deployable capital.
- **Don't recommend a venue in `platforms.blocked[]`.** Filter every rec target against this list.
- **Don't double-count yield.** Apply `data_quirks` rules — typically `get_allocation by:source` is canonical.
- **Don't skip sources.** Every macro / news / yield claim needs a URL; drop the claim if no source.
- **Don't fabricate figures.** "n/a" beats invented data.
- **Don't write in any language other than `output_language`.** Tickers, platform names, acronyms (FX, DTE, IV, HHI, APY), and code stay as-is.
- **Don't skip the clarify step when triggers fire.** Fabricating a cause for an anomaly is a hard violation.
- **Don't edit `memory/` files from inside the advisor.** Even small fixes route through memory-curator in Step 8.
