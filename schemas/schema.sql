-- Hermes AI Risk Signal Observatory schema v2

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    modality TEXT NOT NULL,
    collector TEXT NOT NULL,
    url TEXT,
    feed_url TEXT,
    priority TEXT NOT NULL CHECK (priority IN ('high','medium','low')),
    refresh_interval TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT true,
    risk_focus JSONB NOT NULL DEFAULT '[]',
    extractor_strategy JSONB NOT NULL DEFAULT '{}',
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS source_health (
    source_id TEXT PRIMARY KEY REFERENCES sources(id) ON DELETE CASCADE,
    last_fetch_at TIMESTAMPTZ,
    last_success_at TIMESTAMPTZ,
    last_error_at TIMESTAMPTZ,
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    status TEXT NOT NULL DEFAULT 'unknown',
    metrics JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS source_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id TEXT NOT NULL,
    source_type TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    items_found INTEGER NOT NULL DEFAULT 0,
    items_new INTEGER NOT NULL DEFAULT 0,
    items_duplicate INTEGER NOT NULL DEFAULT 0,
    items_error INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_source_runs_source_id ON source_runs(source_id);
CREATE INDEX IF NOT EXISTS idx_source_runs_status ON source_runs(status);

CREATE TABLE IF NOT EXISTS raw_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id TEXT NOT NULL REFERENCES sources(id),
    modality TEXT NOT NULL,
    url TEXT,
    canonical_url TEXT,
    title TEXT NOT NULL,
    normalized_title TEXT,
    author TEXT,
    published_at TIMESTAMPTZ,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    language TEXT,
    content_text TEXT,
    content_html TEXT,
    content_hash TEXT,
    dedup_key TEXT,
    metadata JSONB NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'new',
    ingestion_status TEXT NOT NULL DEFAULT 'new',
    duplicate_of UUID REFERENCES raw_items(id),
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    seen_count INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(source_id, canonical_url)
);

CREATE INDEX IF NOT EXISTS idx_raw_items_status ON raw_items(status);
CREATE INDEX IF NOT EXISTS idx_raw_items_published_at ON raw_items(published_at);
CREATE INDEX IF NOT EXISTS idx_raw_items_source_id ON raw_items(source_id);
CREATE INDEX IF NOT EXISTS idx_raw_items_canonical_url ON raw_items(canonical_url);
CREATE INDEX IF NOT EXISTS idx_raw_items_content_hash ON raw_items(content_hash);
CREATE INDEX IF NOT EXISTS idx_raw_items_dedup_key ON raw_items(dedup_key);

CREATE TABLE IF NOT EXISTS event_clusters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    summary TEXT,
    canonical_event_key TEXT UNIQUE,
    entities JSONB NOT NULL DEFAULT '[]',
    risk_domains JSONB NOT NULL DEFAULT '[]',
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS source_claims (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_item_id UUID NOT NULL REFERENCES raw_items(id) ON DELETE CASCADE,
    event_cluster_id UUID REFERENCES event_clusters(id),
    speaker TEXT,
    claim_text TEXT NOT NULL,
    claim_type TEXT NOT NULL,
    risk_domains JSONB NOT NULL DEFAULT '[]',
    entities JSONB NOT NULL DEFAULT '[]',
    evidence_level TEXT NOT NULL,
    evidence_quote TEXT,
    evidence_timestamp TEXT,
    primary_source_url TEXT,
    confidence INTEGER CHECK (confidence BETWEEN 1 AND 5),
    should_promote_to_signal BOOLEAN NOT NULL DEFAULT false,
    needs_human_review BOOLEAN NOT NULL DEFAULT false,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_source_claims_raw_item ON source_claims(raw_item_id);
CREATE INDEX IF NOT EXISTS idx_source_claims_event_cluster ON source_claims(event_cluster_id);

CREATE TABLE IF NOT EXISTS signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_cluster_id UUID REFERENCES event_clusters(id),
    title_zh TEXT NOT NULL,
    summary_zh TEXT NOT NULL,
    what_changed TEXT NOT NULL,
    why_it_matters TEXT NOT NULL,
    what_to_watch_next TEXT NOT NULL,
    signal_type TEXT NOT NULL,
    risk_domains JSONB NOT NULL DEFAULT '[]',
    entities JSONB NOT NULL DEFAULT '[]',
    source_ids JSONB NOT NULL DEFAULT '[]',
    raw_item_ids JSONB NOT NULL DEFAULT '[]',
    claim_ids JSONB NOT NULL DEFAULT '[]',
    primary_source_url TEXT,
    evidence_level TEXT NOT NULL,
    claim_type TEXT NOT NULL,
    severity INTEGER NOT NULL CHECK (severity BETWEEN 1 AND 5),
    confidence INTEGER NOT NULL CHECK (confidence BETWEEN 1 AND 5),
    time_sensitivity INTEGER NOT NULL CHECK (time_sensitivity BETWEEN 1 AND 5),
    priority_score NUMERIC(5,2) NOT NULL,
    needs_human_review BOOLEAN NOT NULL DEFAULT false,
    status TEXT NOT NULL DEFAULT 'draft',
    signal_date DATE NOT NULL DEFAULT CURRENT_DATE,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_signals_date ON signals(signal_date);
CREATE INDEX IF NOT EXISTS idx_signals_priority ON signals(priority_score DESC);
CREATE INDEX IF NOT EXISTS idx_signals_status ON signals(status);

CREATE TABLE IF NOT EXISTS benchmark_registry (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    risk_domains JSONB NOT NULL DEFAULT '[]',
    source_ids JSONB NOT NULL DEFAULT '[]',
    observation_type TEXT NOT NULL,
    extraction_method TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'medium',
    trigger_rules JSONB NOT NULL DEFAULT '[]',
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS benchmark_observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    benchmark_id TEXT NOT NULL REFERENCES benchmark_registry(id),
    model_name TEXT,
    observed_at DATE,
    value_text TEXT,
    value_numeric NUMERIC,
    unit TEXT,
    source_url TEXT NOT NULL,
    evidence TEXT,
    risk_interpretation TEXT,
    confidence INTEGER CHECK (confidence BETWEEN 1 AND 5),
    raw_item_id UUID REFERENCES raw_items(id),
    signal_id UUID REFERENCES signals(id),
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS digests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    digest_date DATE NOT NULL,
    timezone TEXT NOT NULL DEFAULT 'Asia/Shanghai',
    title TEXT NOT NULL,
    markdown_full TEXT NOT NULL,
    markdown_short TEXT NOT NULL,
    signal_ids JSONB NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(digest_date, timezone)
);

CREATE TABLE IF NOT EXISTS delivery_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    digest_id UUID REFERENCES digests(id) ON DELETE CASCADE,
    channel TEXT NOT NULL,
    target TEXT,
    status TEXT NOT NULL,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    target_type TEXT,
    target_id TEXT,
    payload JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
