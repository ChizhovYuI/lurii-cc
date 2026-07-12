# HTML report styling — superseded

The portfolio HTML report is no longer hand-written or copy-substituted. As of
the render-pipeline change, it is produced deterministically:

- **`report-template.html`** — the design (Tailwind CDN classes, exported from
  Pencil), parameterized with `{{slot}}` and `{{#list}}…{{/list}}` blocks.
- **`render_report.py`** — stdlib renderer. Owns *all* presentation: bar pixel
  widths, APY heat colors, tone → color mapping, timeline split. The model
  never emits colors, pixels, or CSS classes.
- **`report-data.md`** — the JSON data contract the advisor fills.
- **`report-data.example.json`** — canonical reference payload.

**Styling / layout changes** go in `report-template.html` (and
`render_report.py` if a new derived value is needed) — not in per-report output,
and not here. The earlier CSS class catalog described a retired inline-CSS
design and no longer applies.

**Cowork publish:** when `patterns.report_artifact_format` is `cowork`, publish
the rendered `reports/advisor-{date}.html` via `mcp__cowork__create_artifact`
(or `update_artifact` if the id collides). The artifact `id` is the report
filename stem, e.g. `advisor-2026-05-03`.
