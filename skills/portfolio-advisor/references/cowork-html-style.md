# Cowork HTML artifact style

Constraints for the self-contained HTML rendered via `mcp__cowork__create_artifact` (or `update_artifact` if id collides). The `id` matches the report filename stem (e.g. `advisor-2026-05-03`).

- Light color-scheme, white background.
- System sans-serif font stack.
- Max width ~820px; padding ~28px 36px.
- Headings: 24 / 18 / 15 px, weight 500.
- Tables: 1px `#e5e5e5` borders; header background `#f9f9f9`.
- Inline `<code>` for tickers: 13px monospace; background `#f3f3f3`.
- Links: `#2c5cc5`; `target="_blank" rel="noreferrer"`.
- All CSS inline. No external resources, no JS, no markdown library.
- Body order matches the markdown report.
