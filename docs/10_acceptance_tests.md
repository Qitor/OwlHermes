# Acceptance Tests v2

## Round 1 Smoke Tests

- [ ] `docker compose up` starts backend + postgres.
- [ ] DB migration succeeds.
- [ ] Registry loader validates all YAML files.
- [ ] Registry service lists due/high-priority sources for Hermes.
- [ ] Hermes-led dry run can store a discovered raw item.
- [ ] Optional helper failures do not stop the workflow.
- [ ] Dedup prevents same URL duplicate insertion.
- [ ] MCP server starts.
- [ ] Hermes can call `risk_registry_list_due_sources`.
- [ ] Hermes can call `risk_raw_item_seen_check`.
- [ ] Hermes can call `risk_raw_item_store`.
- [ ] Hermes can store claims/signals/digests through MCP.
- [ ] Daily digest created in DB.
- [ ] Delivery event recorded.
- [ ] Website displays latest digest.
- [ ] Source health endpoint returns status for all enabled sources.

## Signal Quality Tests

For a sample of generated signals:

- [ ] Has `what_changed`.
- [ ] Has `why_it_matters`.
- [ ] Has `what_to_watch_next`.
- [ ] Has `primary_source_url`.
- [ ] Has `evidence_level`.
- [ ] Has `claim_type`.
- [ ] Has score fields.
- [ ] High severity / low confidence is marked needs_human_review.
- [ ] Podcast claims include speaker or timestamp if transcript exists.
- [ ] Event signals cite agenda/materials/statement URL.

## Regression Tests

- [ ] Source registry invalid YAML fails fast.
- [ ] Unknown modality fails validation.
- [ ] Optional helper timeout does not stop whole run.
- [ ] Broken source appears in source health.
- [ ] Duplicate news article does not create duplicate signal.
- [ ] Digest can be regenerated idempotently for the same date.
