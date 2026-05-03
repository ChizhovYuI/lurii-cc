# Default clarification-triggers catalog

Offer as a multiSelect `AskUserQuestion`. The user keeps the relevant subset.

| Trigger id | Description |
|-----------|-------------|
| `net_worth_delta_5pct` | Net-worth Δ > 5% vs prior report |
| `source_ghost_movement` | source-level $ delta unexplained by transactions |
| `new_or_zeroed_asset` | asset newly held or dropped to zero with no transaction |
| `macro_event_within_7d` | high-impact macro event within 7 days |
| `top5_holding_event` | top-5 holding earnings / regulatory / >5% single-day move |
| `stale_data` | source > 5% NAV with snapshot age > 7d |
| `horizon_decision_pending` | on-horizon item awaiting user decision |
