# Source Reliability Known Issues

## Frequently Failing Sources

### OpenAI (Cloudflare)
- Direct browser access blocked by Cloudflare
- **Fallback**: Use Yahoo Search to find OpenAI blog posts
- Subagents may burn full timeout budget (600s) trying direct access

### Apollo Blog (403 Forbidden)
- Scrapling helper returns 403
- Direct browse also blocked
- Last post Jan 2026 — check biweekly, not daily

### SAIF/IDAIS (Timeout)
- JS-heavy pages cause browser timeouts
- Subagents should limit iterations before pivoting to search

### AXRP (No Useful RSS)
- Helper returns navigation links, not episode listings
- No RSS feed for episodes
- Check weekly, not daily

### arXiv API (Rate-Limit)
- Use `limit=5-10` for high-volume sources like `ai_safety`
- Payloads can be ~76K chars with `limit=20`
- Lower limits reduce context pressure

## High-Value Sources

### NIST CAISI
- Government eval reports — 2/4 signals in R1-13 run
- High signal density per check

### Anthropic News
- Official announcements including RSP updates
- Scrapling helper returns URLs as titles (must deep-read for actual content)

### TechCrunch RSS
- Consistent feed with broad AI coverage
- "In Brief" articles have low information density — scan before deep-reading

## MCP Backend Failure Patterns

### NoneType Cascade
`risk_raw_item_store` can fail with `'NoneType' object is not subscriptable`. After 3 consecutive failures, the MCP server auto-disconnects.

**Mitigation**:
1. Do NOT batch multiple `risk_raw_item_store` calls
2. If first fails, try simplified payload (remove optional fields)
3. Wait auto-retry window if server disconnects
4. Consider skipping raw_item_store and using signal_store/evidence_store directly

### UUID Format
All ID fields require **full UUID strings** (e.g. `84496323-b568-4a00-b8ed-072236b27295`). Truncated IDs like `"ffc8780d"` cause validation errors.

### digest_store Schema
The `risk_digest_store` tool requires a `digest` JSON parameter with keys `digest_date`, `title`, `body`. Common mistake: passing `date` and `digest` as top-level keys.

### live_daily_report_upsert Naming
Uses `report_date` (not `daily_report_date`). Inconsistent with other tools.
