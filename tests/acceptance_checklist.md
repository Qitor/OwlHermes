# Acceptance Checklist v2

## Required before Round 1 handoff

- [ ] Backend can start locally.
- [ ] Postgres migration applies cleanly.
- [ ] Registry loader loads all four YAML files.
- [ ] Invalid registry entry fails with clear error.
- [ ] At least 8 core web/RSS/arXiv sources fetch successfully.
- [ ] Podcast metadata collector stores at least one episode.
- [ ] Event collector stores [un]prompted or IDAIS page snapshot.
- [ ] Raw item dedup works.
- [ ] Hermes MCP server starts.
- [ ] Hermes can list sources.
- [ ] Hermes can trigger fetch.
- [ ] Hermes can store triage.
- [ ] Daily digest stored in DB.
- [ ] Delivery event recorded.
- [ ] Website shows latest digest and signals.
- [ ] Source health endpoint shows successes/failures.

## Signal card quality

- [ ] Title and summary are Chinese.
- [ ] Has what_changed.
- [ ] Has why_it_matters.
- [ ] Has what_to_watch_next.
- [ ] Has signal_type.
- [ ] Has risk_domains.
- [ ] Has evidence_level.
- [ ] Has claim_type.
- [ ] Has primary_source_url.
- [ ] Has score fields.
- [ ] Human review rules are applied.

## Podcast/Event quality

- [ ] Podcast metadata without transcript does not become high-confidence signal.
- [ ] Transcript claims include speaker/timestamp when available.
- [ ] Event agenda change creates raw item but not necessarily signal.
- [ ] Event statement/material can become signal with evidence.
