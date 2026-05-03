# Report template

Section order. Translate headings to `patterns.output_language`. Tickers and platform names stay in `ticker_language`.

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
(only if material — see Step 7b)

## Sources
Grouped by section.
```
