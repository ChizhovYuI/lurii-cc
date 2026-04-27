# lurii-cc

Claude Code marketplace plugin for **Lurii Finance** personal portfolio management. Bundles four skills and the `lurii-finance` MCP server (`pfm-mcp`) so they're available in any Cowork / Claude Code session — not just inside a specific workspace repo.

## What's inside

### Skills

- **portfolio-advisor** — produces a Russian-language quantitative portfolio review with ranked, sourced recommendations. After data + research are collected, surfaces ambiguities to the user via `AskUserQuestion` (cash anomalies, news with directional ambiguity, horizon items awaiting decision) before writing the report. Saves to `reports/advisor-YYYY-MM-DD.md` AND opens it as a Cowork artifact in the right-side pane (id `advisor-YYYY-MM-DD`); same-day re-runs update the existing artifact. Hands off all `memory/` writes to `memory-curator` at the end. Triggers: "проанализируй портфель", "monthly report", "rebalance", "what should I buy".
- **memory-init** — first-time interactive setup of the `memory/` folder (profile, targets, platforms, patterns, on-horizon). Walks the user through structured questions and writes the five files. Triggers: "initialize memory", `/memory-init`, missing/empty `memory/`.
- **memory-curator** — incremental updates to `memory/` when the user shares profile changes, target changes, executed plans, new platforms, etc. Minimal diffs, CHANGELOG entries, confirms before destructive edits. Also receives handoffs from `portfolio-advisor` after each report. Triggers: "update memory", "remember X", "target changed", "ITOT sold".
- **categorization-curator** — iterates on `lurii-finance` type/category rules end-to-end through the MCP. Fixes `unknown` types, fills missing categories, dedups overlapping rules, links missed cross-source transfers. Always dry-runs before create; confirms before delete. Never writes SQL directly. Triggers: "categorize", "fix unknowns", "audit categories", "rule cleanup", "dedup rules", "link transfer", `/categorize`.

The `memory/` folder in your workspace is the **single source of truth** for investor profile, targets, platforms, and on-horizon plans. The skills no longer mirror state to the MCP-side AI report memory.

### MCP server

`lurii-finance` is wired to the `pfm-mcp` binary on the user's `PATH`. The skills depend on it for portfolio data and categorization:

`get_portfolio_summary`, `get_allocation`, `get_yield_positions`, `get_yield_history`, `get_currency_exposure`, `get_risk_metrics`, `get_pnl`, `get_transactions`, `get_snapshots`, `get_sources`, `categorization_summary`, `list_*_rules`, `dry_run_*_rule`, `create_*_rule`, `delete_*_rule`, `apply_categorization`, `set_transaction_category`, `list_categories`.

### Web research

`portfolio-advisor` uses Cowork's built-in `WebSearch` (and `WebFetch` for full-article extraction) for macro / equities / crypto / FX / yield research. Target depth: 3+ independent sources per theme.

### Report viewer

`portfolio-advisor` renders the finished report as a self-contained HTML Cowork artifact via `mcp__cowork__create_artifact`, light-mode styled, opens in the right-side pane and persists across sessions. The markdown file in `reports/` remains the source of truth — the artifact is the live view of it.

## Requirements

- `pfm-mcp` must be installed and on `PATH` (e.g. `/opt/homebrew/bin/pfm-mcp`):
  ```
  brew install ChizhovYuI/lurii/lurii-pfm
  ```
- The skills assume a workspace folder containing `memory/` and `reports/` at its root. Open whichever folder you want to use as the portfolio root before invoking the skills.
- `WebSearch` and `WebFetch` should be allowed in Cowork (they typically are by default).

## Install

### As a marketplace plugin (Claude Code)

```
/plugin install lurii-cc@ChizhovYuI/lurii-cc
```

Or add the repo as a marketplace and install from there:

```
/plugin marketplace add ChizhovYuI/lurii-cc
/plugin install lurii-cc
```

### As a `.plugin` archive (legacy / Cowork)

Build locally:

```
cd lurii-cc
zip -r lurii-cc.plugin .claude-plugin .mcp.json README.md skills
```

Then double-click the `.plugin` file in Cowork, or drop it into a chat. After install, the skills appear as `lurii-cc:portfolio-advisor`, `lurii-cc:memory-curator`, `lurii-cc:memory-init`, `lurii-cc:categorization-curator` in the skill list.

## Workspace layout

The plugin only ships skill *logic* and MCP wiring. Your private workspace folder owns the data:

```
your-workspace/
├── memory/                    # Long-lived investor context (private)
│   ├── profile.md
│   ├── targets.md
│   ├── platforms.md
│   ├── patterns.md
│   └── on-horizon.md
└── reports/                   # Generated portfolio reports (private)
    └── advisor-YYYY-MM-DD.md
```

Run `memory-init` once on a fresh workspace; `portfolio-advisor` and `memory-curator` take it from there.

## Notes

- Memory files live in the user's workspace folder, not in the plugin.
- Reports are written to `reports/` in the active workspace folder, dated `advisor-YYYY-MM-DD.md`. The Cowork artifact uses the same id (`advisor-YYYY-MM-DD`).
- Language: portfolio reports are in Russian by default (per workspace `memory/patterns.md`); skill bodies and CHANGELOG are in English.

## Related repos

- `ChizhovYuI/lurii-pfm` — Python backend, data collectors, SQLite store, `pfm-mcp` server.
- `ChizhovYuI/lurii-finance` — SwiftUI macOS app.
- `ChizhovYuI/homebrew-lurii` — Homebrew tap for distribution.

## License

MIT
