# MCP Backend Failure Patterns

Observed patterns from daily report runs where the ai_risk_observer MCP server becomes unstable.

## Pattern 1: `risk_raw_item_store` NoneType Error

**Symptom**: `risk_raw_item_store` returns `Error executing tool risk_raw_item_store: 'NoneType' object is not subscriptable`

**Trigger**: Appears to be a backend schema/payload mismatch. Occurs even with minimal payloads containing only required fields (`source_id`, `url`).

**Cascade**: After 3 consecutive failures of ANY MCP tool, the MCP server auto-disconnects. This blocks ALL MCP tools (including `risk_signal_store`, `risk_evidence_store`, `risk_source_run_record`, `risk_digest_store`) for approximately 60 seconds.

**Observed in**: R1-13+ runs (2026-05-06 and potentially earlier)

**Mitigation**:
1. Do NOT batch multiple `risk_raw_item_store` calls. If one fails, stop.
2. Try simplifying payload: remove `published_at`, `evidence_urls`, `risk_relevance`, `notes`, `discovery_method` — use only `source_id`, `url`, `title`, `summary`.
3. If server disconnects, wait the auto-retry window. Do not retry immediately.
4. Skip `raw_item_store` and proceed directly to `risk_signal_store` and `risk_evidence_store` if needed — they may work when raw_item_store doesn't.
5. As last resort, generate the digest without backend persistence.

## Pattern 2: Subagent MCP Tool Conflicts

**Symptom**: Subagent and main agent MCP calls interfere when server is in auto-reconnect state.

**Mitigation**: If MCP is unstable, restrict subagents to browser/search tools only. Main agent handles all MCP persistence after subagents complete.

## Pattern 3: delegate_task Batch Limit

**Symptom**: `"Too many tasks: N provided, but max_concurrent_children is 3"`

**Fix**: Pass at most 3 tasks per `delegate_task` call. Split into multiple calls if needed.
