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
    zone VARCHAR(64),
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    tags JSONB NOT NULL DEFAULT '{}'::jsonb,
    raw_tags JSONB DEFAULT '{}'::jsonb,
    owner VARCHAR(128),
    department VARCHAR(128),
    project VARCHAR(128),
    environment VARCHAR(64) NOT NULL DEFAULT 'unknown',
    cost_center VARCHAR(64),
    tag_quality_score NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
    monthly_cost NUMERIC(18, 4) NOT NULL DEFAULT 0.0000,
    resource_created_at TIMESTAMPTZ,
    first_discovered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_inventory_sync_at TIMESTAMPTZ,
    discovery_source VARCHAR(32) NOT NULL DEFAULT 'BILLING_INFERRED',
    discovery_status VARCHAR(32) NOT NULL DEFAULT 'CONFIRMED',
    resource_metadata JSONB DEFAULT '{}'::jsonb,
    metadata_version VARCHAR(16) NOT NULL DEFAULT '1.0'
);

CREATE INDEX IF NOT EXISTS idx_resources_tags ON cloud_resources USING GIN (tags);
CREATE INDEX IF NOT EXISTS idx_resources_prov_env ON cloud_resources (provider, environment);
CREATE INDEX IF NOT EXISTS idx_resources_owner ON cloud_resources (owner);
CREATE INDEX IF NOT EXISTS idx_res_prov_status ON cloud_resources (provider, status);
CREATE INDEX IF NOT EXISTS idx_res_account_res ON cloud_resources (account_id, resource_id);
CREATE INDEX IF NOT EXISTS idx_res_project ON cloud_resources (project);

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
    recommendation_key VARCHAR(256) NOT NULL DEFAULT gen_random_uuid()::text,
    waste_detection_id UUID REFERENCES waste_detections(id) ON DELETE SET NULL,
    resource_id VARCHAR(512) REFERENCES cloud_resources(resource_id) ON DELETE CASCADE,
    provider VARCHAR(16) NOT NULL,
    account_id VARCHAR(64),
    region VARCHAR(64),
    service_name VARCHAR(128),
    service_category VARCHAR(32),
    resource_name VARCHAR(256),
    strategy_id VARCHAR(64) NOT NULL DEFAULT 'advisory_strategy',
    strategy_version VARCHAR(16) NOT NULL DEFAULT '1.0',
    action_type VARCHAR(32) NOT NULL,
    priority VARCHAR(8) NOT NULL DEFAULT 'P2',
    priority_score NUMERIC(5, 4) NOT NULL DEFAULT 0.5000,
    risk_level VARCHAR(16) NOT NULL DEFAULT 'LOW',
    risk_score NUMERIC(5, 4) NOT NULL DEFAULT 0.2000,
    confidence_score NUMERIC(5, 4) NOT NULL DEFAULT 1.0000,
    status VARCHAR(32) NOT NULL DEFAULT 'PROPOSED',
    current_monthly_cost NUMERIC(18, 4) NOT NULL DEFAULT 0.0000,
    projected_monthly_cost NUMERIC(18, 4) NOT NULL DEFAULT 0.0000,
    estimated_monthly_savings NUMERIC(18, 4) NOT NULL DEFAULT 0.0000,
    estimated_annual_savings NUMERIC(18, 4) NOT NULL DEFAULT 0.0000,
    verified_savings NUMERIC(18, 4),
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    implementation_effort VARCHAR(16) NOT NULL DEFAULT 'LOW',
    title VARCHAR(256) NOT NULL,
    description TEXT NOT NULL,
    remediation_guide TEXT NOT NULL,
    savings_calculation JSONB NOT NULL DEFAULT '{}'::jsonb,
    implementation_guidance JSONB NOT NULL DEFAULT '{}'::jsonb,
    assumptions JSONB NOT NULL DEFAULT '[]'::jsonb,
    evidence_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    tags JSONB NOT NULL DEFAULT '{}'::jsonb,
    endorsed_by VARCHAR(128),
    approved_by VARCHAR(128),
    review_reason VARCHAR(512),
    reviewed_by VARCHAR(128),
    approved_at TIMESTAMPTZ,
    accepted_at TIMESTAMPTZ,
    reviewed_at TIMESTAMPTZ,
    implemented_at TIMESTAMPTZ,
    verified_at TIMESTAMPTZ,
    expiry_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rec_status_priority ON recommendations (status, priority);
CREATE INDEX IF NOT EXISTS idx_rec_prov_savings ON recommendations (provider, estimated_monthly_savings);
CREATE INDEX IF NOT EXISTS idx_rec_strategy_status ON recommendations (strategy_id, status);
CREATE INDEX IF NOT EXISTS idx_rec_key ON recommendations (recommendation_key);

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

-- 18. Resource Topology Relationships Table
CREATE TABLE IF NOT EXISTS resource_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_resource_id VARCHAR(512) NOT NULL REFERENCES cloud_resources(resource_id) ON DELETE CASCADE,
    target_resource_id VARCHAR(512) NOT NULL,
    relationship_type VARCHAR(64) NOT NULL,
    provider VARCHAR(16) NOT NULL,
    discovery_source VARCHAR(32) NOT NULL DEFAULT 'INVENTORY_DISCOVERY',
    confidence NUMERIC(5, 4) NOT NULL DEFAULT 1.0000,
    first_observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    relationship_metadata JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT uq_resource_relationships UNIQUE (source_resource_id, target_resource_id, relationship_type)
);
CREATE INDEX IF NOT EXISTS idx_rel_src_tgt ON resource_relationships (source_resource_id, target_resource_id);
CREATE INDEX IF NOT EXISTS idx_rel_provider_type ON resource_relationships (provider, relationship_type);

-- 19. Inventory Synchronization Runs Table
CREATE TABLE IF NOT EXISTS inventory_sync_runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider VARCHAR(16) NOT NULL,
    discovery_mode VARCHAR(32) NOT NULL DEFAULT 'EXPORT_BASED',
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    source_identifier VARCHAR(256),
    total_discovered INTEGER NOT NULL DEFAULT 0,
    new_resources INTEGER NOT NULL DEFAULT 0,
    updated_resources INTEGER NOT NULL DEFAULT 0,
    stale_resources INTEGER NOT NULL DEFAULT 0,
    relationships_discovered INTEGER NOT NULL DEFAULT 0,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    error_details JSONB NOT NULL DEFAULT '[]'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_sync_prov_status ON inventory_sync_runs (provider, status);

-- 20. Inventory Quality Reports Table
CREATE TABLE IF NOT EXISTS inventory_quality_reports (
    report_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sync_run_id UUID,
    provider VARCHAR(16),
    total_resources INTEGER NOT NULL DEFAULT 0,
    completeness_score NUMERIC(5, 2) NOT NULL DEFAULT 100.00,
    tag_completeness_score NUMERIC(5, 2) NOT NULL DEFAULT 100.00,
    inventory_confidence NUMERIC(5, 4) NOT NULL DEFAULT 1.0000,
    findings_count INTEGER NOT NULL DEFAULT 0,
    critical_findings INTEGER NOT NULL DEFAULT 0,
    high_findings INTEGER NOT NULL DEFAULT 0,
    medium_findings INTEGER NOT NULL DEFAULT 0,
    low_findings INTEGER NOT NULL DEFAULT 0,
    findings_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_inv_qual_prov ON inventory_quality_reports (provider);

-- 21. Waste Detection Runs Table
CREATE TABLE IF NOT EXISTS waste_detection_runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider VARCHAR(16) NOT NULL DEFAULT 'ALL',
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    total_resources_evaluated INTEGER NOT NULL DEFAULT 0,
    findings_created INTEGER NOT NULL DEFAULT 0,
    findings_updated INTEGER NOT NULL DEFAULT 0,
    findings_unchanged INTEGER NOT NULL DEFAULT 0,
    total_estimated_monthly_savings NUMERIC(18, 4) NOT NULL DEFAULT 0.0000,
    detector_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_details JSONB NOT NULL DEFAULT '[]'::jsonb,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_waste_run_prov_status ON waste_detection_runs (provider, status);
CREATE INDEX IF NOT EXISTS idx_waste_run_started ON waste_detection_runs (started_at);

-- 22. Cost Baselines Table
CREATE TABLE IF NOT EXISTS cost_baselines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dimension_type VARCHAR(32) NOT NULL,
    dimension_key VARCHAR(512) NOT NULL,
    provider VARCHAR(16) NOT NULL,
    account_id VARCHAR(64),
    service_name VARCHAR(128),
    region VARCHAR(64),
    resource_id VARCHAR(512),
    window_days INTEGER NOT NULL DEFAULT 30,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    mean NUMERIC(18, 4) NOT NULL DEFAULT 0.0000,
    stddev NUMERIC(18, 4) NOT NULL DEFAULT 0.0000,
    median NUMERIC(18, 4) NOT NULL DEFAULT 0.0000,
    mad NUMERIC(18, 4) NOT NULL DEFAULT 0.0000,
    q1 NUMERIC(18, 4) NOT NULL DEFAULT 0.0000,
    q3 NUMERIC(18, 4) NOT NULL DEFAULT 0.0000,
    iqr NUMERIC(18, 4) NOT NULL DEFAULT 0.0000,
    min_value NUMERIC(18, 4) NOT NULL DEFAULT 0.0000,
    max_value NUMERIC(18, 4) NOT NULL DEFAULT 0.0000,
    sample_count INTEGER NOT NULL DEFAULT 0,
    zero_count INTEGER NOT NULL DEFAULT 0,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    version VARCHAR(16) NOT NULL DEFAULT '1.0',
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_baseline_dim_key_window ON cost_baselines (dimension_key, window_days);
CREATE INDEX IF NOT EXISTS idx_baseline_prov_svc ON cost_baselines (provider, service_name);

-- 23. Anomaly Detection Runs Table
CREATE TABLE IF NOT EXISTS anomaly_detection_runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider VARCHAR(16) NOT NULL DEFAULT 'ALL',
    scope VARCHAR(64) NOT NULL DEFAULT 'FULL',
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    total_series_evaluated INTEGER NOT NULL DEFAULT 0,
    baselines_generated INTEGER NOT NULL DEFAULT 0,
    anomalies_created INTEGER NOT NULL DEFAULT 0,
    anomalies_updated INTEGER NOT NULL DEFAULT 0,
    anomalies_unchanged INTEGER NOT NULL DEFAULT 0,
    anomalies_resolved INTEGER NOT NULL DEFAULT 0,
    total_excess_cost NUMERIC(18, 4) NOT NULL DEFAULT 0.0000,
    detector_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_details JSONB NOT NULL DEFAULT '[]'::jsonb,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_anomaly_run_prov_status ON anomaly_detection_runs (provider, status);
CREATE INDEX IF NOT EXISTS idx_anomaly_run_started ON anomaly_detection_runs (started_at);

-- 24. Recommendation Runs Table
CREATE TABLE IF NOT EXISTS recommendation_runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider VARCHAR(16) NOT NULL DEFAULT 'ALL',
    scope VARCHAR(64) NOT NULL DEFAULT 'FULL',
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    total_evaluated INTEGER NOT NULL DEFAULT 0,
    recommendations_created INTEGER NOT NULL DEFAULT 0,
    recommendations_updated INTEGER NOT NULL DEFAULT 0,
    recommendations_unchanged INTEGER NOT NULL DEFAULT 0,
    recommendations_suppressed INTEGER NOT NULL DEFAULT 0,
    total_monthly_savings NUMERIC(18, 4) NOT NULL DEFAULT 0.0000,
    total_annual_savings NUMERIC(18, 4) NOT NULL DEFAULT 0.0000,
    strategy_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_details JSONB NOT NULL DEFAULT '[]'::jsonb,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_rec_run_prov_status ON recommendation_runs (provider, status);
CREATE INDEX IF NOT EXISTS idx_rec_run_started ON recommendation_runs (started_at);

-- 25. Recommendation Evidence Table
CREATE TABLE IF NOT EXISTS recommendation_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recommendation_id UUID NOT NULL REFERENCES recommendations(id) ON DELETE CASCADE,
    evidence_type VARCHAR(64) NOT NULL,
    waste_detection_id UUID REFERENCES waste_detections(id) ON DELETE SET NULL,
    anomaly_id UUID REFERENCES cost_anomalies(id) ON DELETE SET NULL,
    resource_id VARCHAR(512),
    description TEXT NOT NULL,
    telemetry_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    billing_record_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    confidence_score NUMERIC(5, 4) NOT NULL DEFAULT 1.0000,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_rec_ev_rec_type ON recommendation_evidence (recommendation_id, evidence_type);

-- 26. Recommendation History Table
CREATE TABLE IF NOT EXISTS recommendation_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recommendation_id UUID NOT NULL REFERENCES recommendations(id) ON DELETE CASCADE,
    from_status VARCHAR(32),
    to_status VARCHAR(32) NOT NULL,
    actor VARCHAR(128) NOT NULL,
    action VARCHAR(64) NOT NULL,
    notes TEXT,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_rec_hist_rec_time ON recommendation_history (recommendation_id, created_at);




