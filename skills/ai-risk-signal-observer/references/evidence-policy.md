# Evidence Policy

## Core Rule

**For each Top Signal, you MUST store at least one evidence item.**

Intermediate evidence objects are part of the product — do not only store the final digest.

## Evidence Fields

| Field | Required | Description |
|-------|----------|-------------|
| `claim_text` | Yes | What was claimed or observed |
| `evidence_url` | Recommended | Primary source URL |
| `evidence_excerpt` | Recommended | Relevant excerpt from the source |
| `confidence` | Optional | 1-5 confidence level |
| `supports_signal` | Optional | Whether evidence supports or weakens the signal |
| `risk_domains` | Optional | Relevant risk domains |
| `signal_id` | If linked | UUID of the linked signal |
| `raw_item_id` | If linked | UUID of the linked raw item |

## When Evidence is Missing

If evidence excerpt is unavailable:
- Set `needs_human_review: true`
- Include `needs_review_reason` explaining why excerpt is missing
- Example: "Evidence URL linked but full text not yet captured; paywalled source"

## Evidence Storage

```
owl_risk_state(action="store_evidence", payload={
    "signal_id": "<uuid>",
    "claim_text": "Anthropic updated their RSP to include new capability threshold",
    "evidence_url": "https://anthropic.com/news/rsp-update",
    "evidence_excerpt": "We are adding a new capability threshold for autonomous research...",
    "confidence": 4,
    "supports_signal": true,
    "risk_domains": ["capability_thresholds", "lab_safety_commitments"]
})
```

## Evidence Search

```
owl_risk_state(action="search_evidence", payload={
    "signal_id": "<uuid>",
    "limit": 20
})
```

## Prefer Primary Sources

- Always keep the source URL
- Prefer official pages over news aggregators
- Mark high-impact low-confidence claims as `needs_human_review`
