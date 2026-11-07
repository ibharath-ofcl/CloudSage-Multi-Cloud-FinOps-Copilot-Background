-- ==============================================================================
-- CloudSage PostgreSQL 16+ Declarative Partitioning & Optimization Script
-- Implements FOCUS 1.0 Unified Billing Table with Monthly Range Partitions
-- ==============================================================================

-- 1. Enable Required Extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Create Partitioned Billing Records Table (FOCUS 1.0 Standard)
CREATE TABLE IF NOT EXISTS billing_records (
    record_id UUID NOT NULL DEFAULT gen_random_uuid(),
    provider VARCHAR(16) NOT NULL,
    billing_account_id VARCHAR(64) NOT NULL,
    subscription_id VARCHAR(64) NOT NULL,
    resource_id VARCHAR(512) NOT NULL,
    resource_name VARCHAR(256),
    service_category VARCHAR(32) NOT NULL,
    service_name VARCHAR(128) NOT NULL,
    region VARCHAR(64) NOT NULL,
    zone VARCHAR(64),
    usage_start_time TIMESTAMPTZ NOT NULL,
    usage_end_time TIMESTAMPTZ NOT NULL,
    usage_quantity NUMERIC(18, 6) NOT NULL DEFAULT 0.0,
    usage_unit VARCHAR(32) NOT NULL,
    unblended_cost NUMERIC(18, 4) NOT NULL DEFAULT 0.0000,
    blended_cost NUMERIC(18, 4),
    list_cost NUMERIC(18, 4),
    pricing_model VARCHAR(32) NOT NULL DEFAULT 'ON_DEMAND',
    currency VARCHAR(8) NOT NULL DEFAULT 'USD',
    tags JSONB NOT NULL DEFAULT '{}'::jsonb,
    raw_metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_billing_records PRIMARY KEY (record_id, usage_start_time)
) PARTITION BY RANGE (usage_start_time);

-- 3. Monthly Partitions for Calendar Year 2026
CREATE TABLE IF NOT EXISTS billing_records_y2026m01 PARTITION OF billing_records
    FOR VALUES FROM ('2026-01-01 00:00:00+00') TO ('2026-02-01 00:00:00+00');

CREATE TABLE IF NOT EXISTS billing_records_y2026m02 PARTITION OF billing_records
    FOR VALUES FROM ('2026-02-01 00:00:00+00') TO ('2026-03-01 00:00:00+00');

CREATE TABLE IF NOT EXISTS billing_records_y2026m03 PARTITION OF billing_records
    FOR VALUES FROM ('2026-03-01 00:00:00+00') TO ('2026-04-01 00:00:00+00');

CREATE TABLE IF NOT EXISTS billing_records_y2026m04 PARTITION OF billing_records
    FOR VALUES FROM ('2026-04-01 00:00:00+00') TO ('2026-05-01 00:00:00+00');

CREATE TABLE IF NOT EXISTS billing_records_y2026m05 PARTITION OF billing_records
    FOR VALUES FROM ('2026-05-01 00:00:00+00') TO ('2026-06-01 00:00:00+00');

CREATE TABLE IF NOT EXISTS billing_records_y2026m06 PARTITION OF billing_records
    FOR VALUES FROM ('2026-06-01 00:00:00+00') TO ('2026-07-01 00:00:00+00');

CREATE TABLE IF NOT EXISTS billing_records_y2026m07 PARTITION OF billing_records
    FOR VALUES FROM ('2026-07-01 00:00:00+00') TO ('2026-08-01 00:00:00+00');

CREATE TABLE IF NOT EXISTS billing_records_y2026m08 PARTITION OF billing_records
    FOR VALUES FROM ('2026-08-01 00:00:00+00') TO ('2026-09-01 00:00:00+00');

CREATE TABLE IF NOT EXISTS billing_records_y2026m09 PARTITION OF billing_records
    FOR VALUES FROM ('2026-09-01 00:00:00+00') TO ('2026-10-01 00:00:00+00');

CREATE TABLE IF NOT EXISTS billing_records_y2026m10 PARTITION OF billing_records
    FOR VALUES FROM ('2026-10-01 00:00:00+00') TO ('2026-11-01 00:00:00+00');

CREATE TABLE IF NOT EXISTS billing_records_y2026m11 PARTITION OF billing_records
    FOR VALUES FROM ('2026-11-01 00:00:00+00') TO ('2026-12-01 00:00:00+00');

CREATE TABLE IF NOT EXISTS billing_records_y2026m12 PARTITION OF billing_records
    FOR VALUES FROM ('2026-12-01 00:00:00+00') TO ('2027-01-01 00:00:00+00');

-- Default Partition for catch-all
CREATE TABLE IF NOT EXISTS billing_records_default PARTITION OF billing_records DEFAULT;

-- 4. High-Performance Partitioned Indexes
CREATE INDEX IF NOT EXISTS idx_billing_tags ON billing_records USING GIN (tags);
CREATE INDEX IF NOT EXISTS idx_billing_prov_srv_time ON billing_records (provider, service_category, usage_start_time);
CREATE INDEX IF NOT EXISTS idx_billing_res_time ON billing_records (resource_id, usage_start_time);
CREATE INDEX IF NOT EXISTS idx_billing_time_brin ON billing_records USING BRIN (usage_start_time);

-- 5. Cloud Resources Inventory Table
CREATE TABLE IF NOT EXISTS cloud_resources (
    resource_id VARCHAR(512) PRIMARY KEY,
    provider VARCHAR(16) NOT NULL,
    account_id VARCHAR(64) NOT NULL,
    resource_name VARCHAR(256),
    service_category VARCHAR(32) NOT NULL,
    service_name VARCHAR(128) NOT NULL,
    resource_type VARCHAR(64) NOT NULL,
    region VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    tags JSONB NOT NULL DEFAULT '{}'::jsonb,
    owner VARCHAR(128),
    environment VARCHAR(64) NOT NULL DEFAULT 'unknown',
    cost_center VARCHAR(64),
    monthly_cost NUMERIC(18, 4) NOT NULL DEFAULT 0.0000,
    first_discovered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_resources_tags ON cloud_resources USING GIN (tags);
CREATE INDEX IF NOT EXISTS idx_resources_prov_env ON cloud_resources (provider, environment);
CREATE INDEX IF NOT EXISTS idx_resources_owner ON cloud_resources (owner);

-- 6. Resource Metrics Table
CREATE TABLE IF NOT EXISTS resource_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_id VARCHAR(512) NOT NULL REFERENCES cloud_resources(resource_id) ON DELETE CASCADE,
    metric_name VARCHAR(64) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    average_value NUMERIC(10, 4) NOT NULL,
    peak_value NUMERIC(10, 4) NOT NULL,
    sample_count INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_metrics_res_name_time ON resource_metrics (resource_id, metric_name, timestamp);

-- 7. Waste Detections Table
CREATE TABLE IF NOT EXISTS waste_detections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_id VARCHAR(512) NOT NULL REFERENCES cloud_resources(resource_id) ON DELETE CASCADE,
    provider VARCHAR(16) NOT NULL,
    waste_type VARCHAR(32) NOT NULL,
    severity VARCHAR(16) NOT NULL DEFAULT 'MEDIUM',
    status VARCHAR(16) NOT NULL DEFAULT 'ACTIVE',
    estimated_monthly_waste NUMERIC(18, 4) NOT NULL DEFAULT 0.0000,
    telemetry_proof JSONB NOT NULL DEFAULT '{}'::jsonb,
    dismissal_reason VARCHAR(512),
    dismissed_by VARCHAR(128),
    snooze_until TIMESTAMPTZ,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_waste_active_prov ON waste_detections (status, provider) WHERE status = 'ACTIVE';
CREATE INDEX IF NOT EXISTS idx_waste_type_status ON waste_detections (waste_type, status);

-- 8. Advisory Recommendations Table
CREATE TABLE IF NOT EXISTS recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    waste_detection_id UUID REFERENCES waste_detections(id) ON DELETE SET NULL,
    resource_id VARCHAR(512) NOT NULL REFERENCES cloud_resources(resource_id) ON DELETE CASCADE,
    provider VARCHAR(16) NOT NULL,
    action_type VARCHAR(32) NOT NULL,
    priority VARCHAR(8) NOT NULL DEFAULT 'P2',
    risk_level VARCHAR(16) NOT NULL DEFAULT 'LOW',
    status VARCHAR(16) NOT NULL DEFAULT 'PROPOSED',
    estimated_monthly_savings NUMERIC(18, 4) NOT NULL DEFAULT 0.0000,
    estimated_annual_savings NUMERIC(18, 4) NOT NULL DEFAULT 0.0000,
    implementation_effort VARCHAR(16) NOT NULL DEFAULT 'LOW',
    title VARCHAR(256) NOT NULL,
    description TEXT NOT NULL,
    remediation_guide TEXT NOT NULL,
    endorsed_by VARCHAR(128),
    approved_by VARCHAR(128),
    approved_at TIMESTAMPTZ,
    implemented_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rec_status_priority ON recommendations (status, priority);
CREATE INDEX IF NOT EXISTS idx_rec_prov_savings ON recommendations (provider, estimated_monthly_savings);

-- 9. Cost Anomalies Table
CREATE TABLE IF NOT EXISTS cost_anomalies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider VARCHAR(16) NOT NULL,
    service_category VARCHAR(32) NOT NULL,
    service_name VARCHAR(128) NOT NULL,
    account_id VARCHAR(64) NOT NULL,
    region VARCHAR(64) NOT NULL,
    anomaly_date DATE NOT NULL,
    actual_cost NUMERIC(18, 4) NOT NULL,
    expected_cost NUMERIC(18, 4) NOT NULL,
    baseline_mean NUMERIC(18, 4) NOT NULL,
    baseline_stddev NUMERIC(18, 4) NOT NULL,
    z_score NUMERIC(8, 4) NOT NULL,
    spike_percentage NUMERIC(8, 2) NOT NULL,
    severity VARCHAR(16) NOT NULL DEFAULT 'MEDIUM',
    status VARCHAR(16) NOT NULL DEFAULT 'OPEN',
    root_cause_analysis JSONB NOT NULL DEFAULT '{}'::jsonb,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_anomaly_status_date ON cost_anomalies (status, anomaly_date);

-- 10. Users Table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(256) UNIQUE NOT NULL,
    full_name VARCHAR(128) NOT NULL,
    hashed_password VARCHAR(256) NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'FINANCE_ANALYST',
    department VARCHAR(64),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 11. Audit Logs Table
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    user_email VARCHAR(256),
    action_type VARCHAR(64) NOT NULL,
    resource_type VARCHAR(64) NOT NULL,
    resource_id VARCHAR(512),
    before_state JSONB,
    after_state JSONB,
    client_ip VARCHAR(64),
    status VARCHAR(16) NOT NULL DEFAULT 'SUCCESS'
);

CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_logs (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_logs (user_id, timestamp);

-- 12. Alert Rules & Notification Logs
CREATE TABLE IF NOT EXISTS alert_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(128) NOT NULL,
    alert_type VARCHAR(32) NOT NULL,
    threshold_value NUMERIC(18, 4) NOT NULL,
    channels JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS notification_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_rule_id UUID REFERENCES alert_rules(id) ON DELETE SET NULL,
    channel VARCHAR(32) NOT NULL,
    recipient VARCHAR(256) NOT NULL,
    payload JSONB NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'DELIVERED',
    dispatched_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 13. Ingestion Runs & Telemetry Table
CREATE TABLE IF NOT EXISTS ingestion_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider VARCHAR(16) NOT NULL,
    source_filename VARCHAR(256) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'RUNNING',
    total_records INTEGER NOT NULL DEFAULT 0,
    ingested_records INTEGER NOT NULL DEFAULT 0,
    duplicate_records INTEGER NOT NULL DEFAULT 0,
    failed_records INTEGER NOT NULL DEFAULT 0,
    total_cost NUMERIC(18, 4) NOT NULL DEFAULT 0.0000,
    checksum VARCHAR(64),
    error_summary JSONB,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_ingest_prov_status ON ingestion_runs (provider, status);
CREATE INDEX IF NOT EXISTS idx_ingest_started_at ON ingestion_runs (started_at);

-- 14. Currency Exchange Rates Table
CREATE TABLE IF NOT EXISTS exchange_rates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    currency_code VARCHAR(3) NOT NULL,
    effective_date DATE NOT NULL,
    rate_to_usd NUMERIC(18, 6) NOT NULL,
    source VARCHAR(64) NOT NULL DEFAULT 'ECB_REFERENCE',
    is_interpolated BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_exchange_rates_curr_date ON exchange_rates (currency_code, effective_date);

-- 15. SKU Catalog Mappings Table
CREATE TABLE IF NOT EXISTS sku_catalog_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider VARCHAR(16) NOT NULL,
    service_code VARCHAR(128) NOT NULL,
    sku_id VARCHAR(256),
    canonical_category VARCHAR(32) NOT NULL,
    service_family VARCHAR(64) NOT NULL,
    resource_type VARCHAR(64) NOT NULL,
    normalized_unit VARCHAR(32) NOT NULL,
    pricing_model_default VARCHAR(32),
    confidence NUMERIC(5, 4) NOT NULL DEFAULT 1.0000,
    provenance VARCHAR(32) NOT NULL DEFAULT 'SYSTEM_CATALOG',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sku_catalog_lookup ON sku_catalog_mappings (provider, service_code, sku_id);

-- 16. Normalization Runs Table
CREATE TABLE IF NOT EXISTS normalization_runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    normalization_version VARCHAR(16) NOT NULL DEFAULT '1.0.0',
    mapping_version VARCHAR(16) NOT NULL DEFAULT '2026.11',
    total_records INTEGER NOT NULL DEFAULT 0,
    successful_records INTEGER NOT NULL DEFAULT 0,
    failed_records INTEGER NOT NULL DEFAULT 0,
    warnings_count INTEGER NOT NULL DEFAULT 0,
    average_quality_score NUMERIC(5, 2) NOT NULL DEFAULT 100.00,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    error_details JSONB NOT NULL DEFAULT '[]'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_norm_status ON normalization_runs (status);

-- 17. Data Quality Reports Table
CREATE TABLE IF NOT EXISTS data_quality_reports (
    report_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID,
    provider VARCHAR(16),
    overall_score NUMERIC(5, 2) NOT NULL DEFAULT 100.00,
    total_records_evaluated INTEGER NOT NULL DEFAULT 0,
    critical_findings INTEGER NOT NULL DEFAULT 0,
    high_findings INTEGER NOT NULL DEFAULT 0,
    medium_findings INTEGER NOT NULL DEFAULT 0,
    low_findings INTEGER NOT NULL DEFAULT 0,
    informational_findings INTEGER NOT NULL DEFAULT 0,
    findings_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_dq_provider ON data_quality_reports (provider);

