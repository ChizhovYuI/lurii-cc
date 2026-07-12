# Report data contract (HTML render)

The HTML report is produced by a renderer, not by regenerating markup. The
advisor emits a compact JSON payload; `reports/render_report.py` computes all
presentational values (bar pixel widths, APY heat colors, tone → color) and
fills `reports/report-template.html`.

**Render command.** `render_report.py` and `report-template.html` ship in this
skill's `references/` dir; the script auto-finds the template beside itself, so
pass only the data file. `$REF` = the absolute path of this skill's `references`
directory (resolve it from where the skill is loaded); output goes to the
workspace `reports/`:

```
python3 "$REF/render_report.py" reports/advisor-{date}.data.json > reports/advisor-{date}.html
```

Emit **only semantic values**: numbers, short text, and `tone` enums. Never
hand-write hex colors or pixel widths — the renderer owns those. Text is
HTML-escaped automatically, so write `>` and `&` literally.

## Tone enums

`tone` picks a color family. Valid: `good` (green), `warn` (amber), `bad`
(red), `neutral` (grey), `info` (blue). Translate visible text to
`patterns.output_language`; keep tickers/platforms in `ticker_language`.

## Top-level keys

`doc_title` · `hero` · `actions` · `composition` · `market` · `yield_matrix`
· `gaps` · `macro` · `changes` · `footer`. Omit any top-level section to drop
it from the page.

### hero
- `eyebrow`, `net_worth`, `meta` — strings.
- `mtd`, `vs` — `{label, tone}` pills (month-to-date; vs prior report).
- `snapshot[]` — 4 cards `{label, value, sub, tone?}`. `tone` colors the value
  (default ink); use `info` for dry-powder, `bad` for a breached cap, etc.

### actions
- `kicker`, `title`, `sub` — strings.
- `featured` — the priority-1 card: `{num, title, action_label, impact_label,
  impact_value, text, caveat?, tone}`. `caveat` optional (amber callout).
- `recs[]` — remaining cards `{num, title, action_label, text, tone}`.
  `tone` drives the number bubble + action pill (EXECUTE→`good`, DEFER/WATCH→
  `warn`, HOLD→`neutral`).

### composition
- `allocation[]` — stacked bar `{category, pct}` (numeric pct). `category` ∈
  `stocks|fiat|crypto|deposit` → fixed color; widths computed from pct.
- `legend[]` — `{category, name, value}` (value is the full `"68.5% · $47,141"`).
- `top_cap_pct` — single-holding cap (bar reads share / cap).
- `top_positions[]` — `{ticker, pct, usd, category}` (numeric pct for bar+label).

### market
- `btc` — `{price, meta, band_frac, totals, pill_label, tone}`. `band_frac`
  0..1 = position of BTC within its target band.
- `fng` — `{value, label, note, tone}` (Fear & Greed; `tone` colors value+label).
- `yields` — `{benchmark_label, value, best_label, best_value, note}`.

### yield_matrix
- `venues[]` — columns `{key, name, sub?}` (`sub` e.g. "bonus"/"locked").
- `rows[]` — `{asset, cells}` where `cells` maps venue `key` →
  `{apy?, usd?, note?}`. Omit `apy` (or `{}`) for an empty "—" cell. Heat
  color is bucketed from `apy` (≥12 best · 9–12 good · 7–9 mid · 4–7 low ·
  <4 faint). `usd` and `note` are independently optional.
- `legend_note` — string under the heat legend.
- `summary[]` — 2 cards `{label, value, note}` (benchmark, rotations).

### gaps
- `risk[]` — 3 metric cards `{label, value, sub, tone, badge_label}`
  (`badge_label` e.g. "OK"/"FLAG"; `tone` colors the badge).
- `list[]` — gap rows `{name, sub, bar, fill_frac, mark_frac?, delta,
  delta_tone, tone, note}`.
  - `bar` ∈ `over|ontarget|fiat|base` → fill color.
  - `fill_frac` 0..1 = bar length; `mark_frac` 0..1 = target tick (optional).
  - `tone` colors the row background; `delta_tone` colors the bold delta text
    independently (a neutral row can carry a green delta).

### macro
- `events[]` — `{date, title, detail, rel, when}`; `when` ∈ `past|future`
  (renderer splits them around the "today" marker and colors accordingly).
- `today_label`, `takeaway` — strings.

### changes
- `kicker` — e.g. `"vs 25 ИЮНЯ 2026"`.
- `rows[]` — each `{cards: [{label, from, to, note, tone}]}` (3 cards/row).
  `tone` colors the card background (`warn` for a breach, else `neutral`).

### footer
- `tx_label`, `tx_text`, `colophon` — strings.
- `sources[]` — `{heading, links: [{text}]}` grouped source columns.

## Reference example

`reports/report-data.example.json` is the 2026-07-11 report. Rendering it with
`report-template.html` reproduces the original Pencil export pixel-for-pixel —
use it as the canonical shape when building a new report's data file.
