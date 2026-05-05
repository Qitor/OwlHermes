# Daily Signal Collection Prompt

Use the Hermes AI Risk Signal Observer skill.

1. Call `risk_fetch_recent` for the last 36 hours.
2. Read new raw items with `risk_raw_items_list`.
3. Triage each item into non-signal, claim, or signal.
4. For podcast/event items, use the dedicated podcast/event extraction rules.
5. Store triage with `risk_triage_store` or claim storage endpoint.
6. Search candidate signals and generate digest.
7. Create digest with `risk_daily_digest_create`.
8. Send digest via configured Hermes gateway.
9. Record delivery with `risk_digest_publish_status`.

Never include unsupported claims. If primary source is missing, reduce confidence or mark needs_human_review.
