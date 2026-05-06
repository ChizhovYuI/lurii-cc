# Cowork HTML artifact style

Constraints for the self-contained HTML rendered via `mcp__cowork__create_artifact` (or `update_artifact` if id collides). The `id` matches the report filename stem (e.g. `advisor-2026-05-03`).

**Use `references/report-template.html` as starting point** — copy it and replace `{{PLACEHOLDER}}` markers with actual data. Everything below describes the contract the template encodes.

## Global constraints

- Self-contained HTML; **no external resources, no JS, no markdown library**.
- Light color-scheme; white background; system sans-serif font stack.
- All CSS inline at the top (single `<style>` block). Do not split into external `.css`.
- Max width ~820px; padding ~28px 36px.
- Body order matches the markdown report.
- Mobile fallback (≤600px) is built in — don't strip it.

## Color tokens

| Purpose | Hex | Use |
|---------|-----|-----|
| Primary blue | `#2c5cc5` | Links, NOW marker, accent borders |
| Success green | `#2a6b2a` | Positive deltas, OK pills |
| Warn amber | `#8a5300` | At-cap warnings, defer pills |
| Critical red | `#a02020` | Negative deltas, retracted, lockdown |
| Stocks blue | `#5b8bd6` | Category donut + bars |
| Fiat amber | `#d6a85b` | Category donut + bars |
| Crypto purple | `#8e5bd6` | Category donut |
| Deposit teal | `#5bc299` | Category donut, OK risk fill |
| DeFi pink | `#d65b8b` | Category donut |
| Card border | `#e8e8e8` | All card outlines |
| Track gray | `#f3f3f3` | Bar/track backgrounds |

## Section catalog

The template ships **11 section types** (2–10 cards each). Pick what your data needs.

| # | Section | Key classes |
|---|---------|-------------|
| Hdr | Title + meta | `h1`, `.meta` |
| Cor | Corrections (collapsible) | `.corrections-banner`, `details.correction-toggle.r1/r2/r3` |
| 1 | Snapshot | `.snap-grid`, `.snap-card`, `.nw-value`, `.donut`, `.bar-row`, `.risk-row`, `.split-row`, `.tx-card` |
| 2 | Macro context | `.ms-strip`, `.ms-card.passed/upcoming/critical`, `.ms-divider`, `.macro-grid`, `.macro-card`, `.tbill-card`, `.lockdown-bar`, `.takeaway` |
| 3 | Equities | `.gap-card`, `.holdings-grid`, `.holding-card.featured`, `.hc-action.hold/add/trim/sell/wait`, `.hc-delta.pos/neg/flat` |
| 4 | Crypto | `.crypto-grid`, `.crypto-card.btc-feature`, `.fg-svg` (gauge), `.btc-gap-track`, `.breakdown-row`, `.anomaly-note` |
| 5 | FX | `.fx-grid`, `.fx-card`, `.fx-pair-pill.fx-locked/fx-flat`, `.fx-range`, `.fx-range-current[data-label]`, `.fx-range-target` |
| 6 | Yields | `.yield-matrix`, `.ym-cell.heat-best/good/mid/low/bad/empty`, `.ym-cell.atcap/headroom/expiry`, `.yield-legend`, `.yield-summary-row` |
| 7 | Gaps & risks | `.gap-list`, `.gap-item.warn/crit`, `.gap-item-fill.surplus/deficit/atlimit/under`, `.gap-item-mark.target` |
| 8 | Recommendations | `.rec.exec/defer/hold/retracted`, `.rec-prio`, `.rec-action-pill.exec-now/defer-pill/hold-pill/wait-pill/retracted-pill`, `.rec-impact` |
| 9 | Changes (drift) | `.drift-banner`, `.drift-grid`, `.drift-card.flag`, `.dv .from / .arrow` |
| 10 | Sources | `.sources-grid`, `.src-block` (icon prefix in `<h3>`) |

## Computed values reference

Several blocks need precomputed widths/positions. Cheat-sheet:

| Block | Formula |
|-------|---------|
| Donut conic stops | Cumulative percentages 0..100 (e.g. stocks 68.5 → fiat 86.58 → crypto 95.10 → ...) |
| Top-5 bar width | `(holding_pct / single_holding_max_pct) * 100` (default cap 20%) |
| Risk gauge fill | `(current / cap) * 100`. Use `ok` if <60%, `warn` 60–95%, `flag` >95% |
| Gap-card bar width | `(current_pct / target_pct) * 100`; target marker at `left: 100%` |
| BTC gap fill width | `(current_pct / max_target_pct) * 100`; per-tier marks at `(tier_pct / max_target_pct) * 100` |
| F&G gauge dashoffset | `157 - (value / 100) * 157` (pathLength=157) |
| F&G gauge needle rotate | `-180 + (value / 100) * 180` degrees |
| FX range marker | `(rate - range_low) / (range_high - range_low) * 100` |
| Heatmap cell heat | `≥12% best / 9–12% good / 7–9% mid / 4–7% low / <4% bad / no position empty` |

## Action / status pills (taxonomy)

Stable across all sections so colors match meaning:

| Pill | Color | Semantic |
|------|-------|----------|
| `EXECUTE NOW` / `exec-now` | green | Today, no event blocks it |
| `DEFER → DATE` / `defer-pill` | amber | Wait for specific window |
| `HOLD` / `hold-pill` | gray | No action, monitor |
| `EARNINGS WAIT` / `wait-pill` | blue | Position-specific catalyst window |
| `RETRACTED` / `retracted-pill` | red | Superseded by correction |

For holdings grid (`.hc-action`):

| Class | Color | Use |
|-------|-------|-----|
| `hold` | gray | No change |
| `add` | green | Buy / fill gap |
| `trim` | amber | Reduce above cap |
| `sell` | red | Close position |
| `wait` | blue | Earnings / regulatory window |

## What stays vs translates

- **Translate to `patterns.output_language`:** all section h2s, card h4 labels (e.g. "Net Worth", "Buffer", "Top-5 holdings"), prose body text, takeaway / lockdown / anomaly text.
- **Stay in `ticker_language` (default English):** tickers (`VTI`, `BTC`), platform names (`CoinEx`, `MEXC`), acronyms (`HHI`, `APY`, `T-Bill`, `NFP`, `FOMC`, `FX`), code identifiers in `<code>` tags, status pill labels (`EXECUTE NOW`, `HOLD`, etc.).

## Optional / omitted blocks

Drop the block entirely (not just its content) when:

- Corrections — no corrections this run
- VXUS gap-card — no `direction: increase` target with material gap
- FX lockdown banner — no upcoming macro events affecting FX
- Anomaly-note — no get_pnl / snapshot quirks worth flagging
- Drift section — no material change AND no minor drifts to record
- T-bill featured card — only when relevant for stable comparison

When dropping, also delete adjacent commentary/transitions in surrounding sections.

## Doctype, language, viewport

```html
<!DOCTYPE html>
<html lang="ru">  <!-- or whatever patterns.output_language is -->
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Портфельный отчёт — YYYY-MM-DD</title>
```

`viewport` is required for the mobile media query to fire correctly inside Cowork.
