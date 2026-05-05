# Daily Report

## Tool Calls

Calling tool risk_source_health_summary...
Result: {"helper_coverage": {"source:rss": 1, "source:scrapling_official_page": 2}, "ok": true}

Calling tool risk_registry_list_due_sources...
Result: {"sources": ["anthropic_news", "openai_news", "techcrunch_ai"]}

Calling tool risk_discovery_helper_preview with source_id="anthropic_news"...
Result: {"candidates": ["url1", "url2"]}

Calling tool risk_discovery_helper_preview with source_id="openai_news"...
Result: {"candidates": ["url3"]}

Calling tool risk_raw_item_seen_check with url="example-item"...
Result: {"seen": false}

Calling tool risk_raw_item_store with source_id="anthropic_news"...
Result: {"id": "abc123", "is_duplicate": false}

Calling tool risk_source_run_record with source_id="anthropic_news"...
Result: {"id": "run1"}

Calling tool risk_signal_store with title="something happened"...
Result: {"id": "sig1"}

Calling tool risk_signal_store with title="another thing"...
Result: {"id": "sig2"}

Calling tool risk_digest_store with status="local_daily_report"...
Result: {"id": "dig1"}

## Notes

I checked some sources today and found a few things.
