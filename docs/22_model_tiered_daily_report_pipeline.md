# R1-11B: Model-Tiered Daily Report Pipeline

## Why Model Tiering

The daily report system has a quality rubric and checker, but Hermes runs can be slow and may time out. Model tiering allows a small/fast model to handle low-risk advisory tasks, freeing Hermes (the strong model) for judgment-heavy work.

## Three Tiers

| Tier | Responsible for | Example |
|------|----------------|---------|
| **Strong model (Hermes)** | Final risk signal judgment, what changed/why it matters/what to watch next, final Chinese report writing, final decision to store signals | "This is a signal because it changes the frontier lab safety commitment landscape" |
| **Small/fast model** | Candidate summaries, evidence excerpts, source-page summaries, lightweight relevance classification, non-authoritative pre-triage | "This article mentions AI safety regulation — possibly relevant" |
| **Deterministic Python** | Dedup, source health, helper preview, quality checks, DB state, artifact writing | URL canonicalization, seen-check, quality scoring |

## What Small Models May Do (Advisory Only)

- Summarize long candidate text
- Extract evidence excerpts from lengthy articles
- Suggest possible risk domains for a candidate
- Provide lightweight relevance classification (possibly relevant / likely not relevant)

## What Small Models Must NOT Do

- Make final risk signal decisions
- Determine severity or confidence scores
- Write final report sections
- Replace Hermes judgment on what counts as a signal

## Safety Constraints

- Small models must NOT make final risk signal decisions — that is Hermes' role
- Small model output is always marked `advisory_only: true`
- Final signal inclusion must still satisfy: what changed / why it matters / what to watch next
- If small model is unavailable, the system falls back to deterministic truncation
- No small model call is required for the system to work
- API keys are never logged or printed

## Expected Speed Benefits

- Pre-processing long articles before Hermes reads them can reduce context consumption
- Lightweight classification helps Hermes skip clearly irrelevant candidates
- Reduces the number of deep research calls Hermes needs to make
- Overall run time should decrease from 15-30 minutes toward 10-20 minutes

## Configuration

Set these environment variables (all optional, small model disabled by default):

```bash
AIRO_ENABLE_SMALL_MODEL=true        # Enable small model tier (default: false)
AIRO_SMALL_MODEL_PROVIDER=openai    # Provider type (default: openai)
AIRO_SMALL_MODEL_NAME=gpt-4o-mini   # Model name
AIRO_SMALL_MODEL_BASE_URL=          # Optional: custom OpenAI-compatible endpoint
AIRO_SMALL_MODEL_API_KEY_ENV=OPENAI_API_KEY  # Name of env var with API key
AIRO_STRONG_MODEL_NAME=             # Metadata only
AIRO_SMALL_MODEL_TIMEOUT_SECONDS=60 # Request timeout
AIRO_SMALL_MODEL_MAX_CONCURRENCY=2  # Max concurrent requests
AIRO_SMALL_MODEL_DRY_RUN=true       # Dry-run mode for tests
```

### Using a local or custom endpoint

Set `AIRO_SMALL_MODEL_BASE_URL` to any OpenAI-compatible endpoint:

```bash
AIRO_SMALL_MODEL_BASE_URL=https://your-endpoint.example.com/v1
AIRO_SMALL_MODEL_NAME=glm4.5-air
AIRO_SMALL_MODEL_API_KEY_ENV=INF_API_KEY
```

### Disabling

Simply leave `AIRO_ENABLE_SMALL_MODEL` unset or set to `false`. The system will use deterministic fallbacks.

## How This Interacts with Hermes Auxiliary Model Slots

Hermes-Agent has its own auxiliary model configuration for internal tasks (context compression, skill search). The R1-11B model tiering is **separate from** Hermes auxiliary model slots:

- Hermes auxiliary models are configured in `~/.hermes/config.yaml`
- R1-11B small model is configured via environment variables and accessed through the `risk_candidate_preprocess` MCP tool
- Hermes calls `risk_candidate_preprocess` as a regular MCP tool
- The backend handles the small model call internally

## Why Small Model Output Is Advisory Only

Small models lack the reasoning depth to make risk judgments. They can:
- Identify that an article mentions "AI safety regulation"
- But cannot determine whether a regulatory change "shifts the risk landscape"

The quality rubric requires every signal to answer three questions with evidence. Small models cannot meet this bar. Their role is to reduce reading burden, not to replace judgment.

## MCP Tool: risk_candidate_preprocess

```
risk_candidate_preprocess(
    title: str,
    url: str = "",
    content_text: str = "",
    source_id: str = "",
    focus: str = "",
    risk_domain: str = "",
) -> {
    ok: bool,
    short_summary: str,
    evidence_excerpt: str,
    possible_risk_domains: list[str],
    advisory_relevance: str,      # "possibly_relevant" / "likely_not_relevant" / "unknown"
    advisory_confidence: int,     # 0-5 (advisory only)
    notes: str,
    model_used: str | null,       # null if fallback used
    advisory_only: true,          # Always true
}
```

- Does NOT store anything
- Does NOT make final risk judgments
- Does NOT call external web (no browsing)
- Falls back deterministically if small model is disabled
