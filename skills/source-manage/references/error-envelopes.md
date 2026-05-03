# Error envelope reference

All MCP source CRUD tools return errors as `{"error": "<message>", ...}` instead of raising. Match on the message prefix to decide the next step.

| Trigger | Error envelope | Recovery |
|---------|----------------|----------|
| Daemon down on `add_source` | `auto_refresh.collect == "skipped", reason: "daemon unreachable"` | Source row written. Tell the user to `pfm refresh --source <name>` once the daemon is up. |
| Cash source already exists | `{"error": "Cash source already exists: <name>"}` | Don't try to delete the existing one. Surface message + the existing name. Stop. |
| Rename collision | `{"error": "Source 'X' already exists"}` | Re-prompt for a different name. |
| Source not found (update / delete) | `{"error": "Source 'X' not found"}` | Re-show the Step 1 source table; re-prompt. |
| Missing required field on add | `{"error": "Missing required field: <name>"}` | Re-loop Step 2A to collect the one field; preserve already-entered values. |
| Unknown source type | `{"error": "Unknown source type: '...'", "valid_types": [...]}` | Re-prompt with returned `valid_types`. |
| Cascade refused | `{"error": "Source 'X' has N transaction(s) and M snapshot(s). Pass cascade=true...", "tx_count": N, "snap_count": M}` | Surface counts and re-ask whether to escalate. |
