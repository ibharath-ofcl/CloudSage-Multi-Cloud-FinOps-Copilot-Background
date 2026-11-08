/**
 * CloudSage Stage 11: Enterprise Recommendation & Waste Workspace Types.
 */

export interface MetricDataPoint {
  timestamp: string;
  average: number;
  peak: number;
  samples: number;
}

export interface MetricSummaryStats {
  min: number;
  max: number;
  avg: number;
  latest: number;
  total_points: number;
  latest_timestamp?: string;
}

export interface ResourceTelemetryData {
  resource_id: string;
  resource_found: boolean;
  has_telemetry: boolean;
  provider?: string;
  service_name?: string;
  status?: string;
  reason?: string;
  message?: string;
  observation_window_days?: number;
  metrics: Record<string, MetricDataPoint[]>;
  summary: Record<string, MetricSummaryStats>;
}

export interface SavingsOverrideItem {
  id: string;
  recommendation_id: string;
  original_monthly_savings: number;
  proposed_monthly_savings: number;
  reason: string;
  proposed_by: string;
  approved_by?: string | null;
  status: 'PROPOSED' | 'APPROVED' | 'REJECTED';
  rejection_reason?: string | null;
  created_at: string;
  reviewed_at?: string | null;
}

export interface RemediationPlaybook {
  format: 'terraform' | 'cloudformation' | 'aws_cli' | 'azure_cli' | 'gcp_cli' | 'bicep' | 'markdown';
  content: string;
  filename: string;
  mime_type: string;
  provider: string;
  action_type: string;
  estimated_monthly_savings: string;
}

export interface RecommendationHistoryItem {
  id: string;
  recommendation_id: string;
  from_status?: string | null;
  to_status: string;
  actor: string;
  action: string;
  notes?: string | null;
  details: Record<string, any>;
  created_at: string;
}

export interface RecommendationEvidenceItem {
  id: string;
  recommendation_id: string;
  evidence_type: string;
  description: string;
  telemetry_data: Record<string, any>;
  billing_record_ids: string[];
  confidence_score: number;
  created_at: string;
}

export interface RecommendationWorkspaceItem {
  id: string;
  recommendation_key?: string;
  resource_id?: string | null;
  provider: 'AWS' | 'AZURE' | 'GCP';
  account_id?: string | null;
  region?: string | null;
  service_name?: string | null;
  service_category?: string | null;
  resource_name?: string | null;
  action_type: string;
  priority: 'P1' | 'P2' | 'P3' | 'P4' | 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  risk_level: 'NONE' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  status: 'NEW' | 'PROPOSED' | 'UNDER_REVIEW' | 'ENDORSED' | 'APPROVED' | 'ACCEPTED' | 'IN_PROGRESS' | 'IMPLEMENTED' | 'VERIFIED' | 'DISMISSED' | 'REJECTED' | 'SNOOZED' | 'EXPIRED' | 'REOPENED';
  estimated_monthly_savings: number;
  estimated_annual_savings: number;
  revised_monthly_savings?: number | null;
  is_savings_overridden?: boolean;
  current_monthly_cost?: number;
  projected_monthly_cost?: number;
  verified_savings?: number | null;
  implementation_effort: string;
  title: string;
  description: string;
  remediation_guide: string;
  savings_calculation?: Record<string, any>;
  implementation_guidance?: Record<string, any>;
  assumptions?: string[];
  evidence_summary?: Record<string, any>;
  tags?: Record<string, any>;
  snooze_until?: string | null;
  assigned_to?: string | null;
  external_ticket_ref?: string | null;
  approved_by?: string | null;
  endorsed_by?: string | null;
  reviewed_by?: string | null;
  review_reason?: string | null;
  created_at: string;
  updated_at?: string | null;
  evidence_items?: RecommendationEvidenceItem[];
  history_items?: RecommendationHistoryItem[];
  savings_overrides?: SavingsOverrideItem[];
}

export interface WasteFindingWorkspaceItem {
  id: string;
  resource_id: string;
  provider: 'AWS' | 'AZURE' | 'GCP';
  account_id?: string | null;
  resource_type?: string | null;
  detector_id?: string | null;
  detector_version: string;
  waste_type: string;
  finding_title?: string | null;
  explanation?: string | null;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFORMATIONAL';
  status: 'ACTIVE' | 'OPEN' | 'ACKNOWLEDGED' | 'ASSIGNED' | 'SNOOZED' | 'DISMISSED' | 'RESOLVED' | 'REOPENED';
  confidence_score: number;
  estimated_monthly_savings: number;
  observation_window_days: number;
  data_quality_status: string;
  requires_human_review: boolean;
  telemetry_proof: Record<string, any>;
  dismissal_reason?: string | null;
  dismissed_by?: string | null;
  snooze_until?: string | null;
  assigned_to?: string | null;
  resolved_by?: string | null;
  resolved_at?: string | null;
  reopened_by?: string | null;
  reopened_at?: string | null;
  action_notes?: string | null;
  first_detected_at: string;
  last_evaluated_at: string;
}

export interface BatchReviewRequest {
  recommendation_ids: string[];
  action: 'APPROVE' | 'REJECT' | 'DISMISS' | 'SNOOZE' | 'ENDORSE';
  actor_email: string;
  reason?: string;
  snooze_days?: number;
  assigned_to?: string;
  external_ticket_ref?: string;
}

export interface BatchReviewResponse {
  total_requested: number;
  total_successful: number;
  total_failed: number;
  successful: Array<{ id: string; status: string; title: string; estimated_monthly_savings: number }>;
  failed: Array<{ id: string; error: string }>;
}

export interface BatchWasteActionRequest {
  finding_ids: string[];
  action: 'ACKNOWLEDGE' | 'ASSIGN' | 'SNOOZE' | 'DISMISS' | 'RESOLVE' | 'REOPEN';
  actor: string;
  reason?: string;
  snooze_days?: number;
  assigned_to?: string;
}

export interface BatchWasteActionResponse {
  total_requested: number;
  total_successful: number;
  total_failed: number;
  successful: Array<{ id: string; resource_id: string; status: string; assigned_to?: string }>;
  failed: Array<{ id: string; error: string }>;
}

export interface EntityCorrelations {
  resource_id: string;
  resource_exists: boolean;
  resource?: {
    resource_id: string;
    provider: string;
    service_name: string;
    account_id: string;
    region: string;
    environment: string;
    owner: string;
    status: string;
    monthly_cost: number;
    tags: Record<string, any>;
  } | null;
  financial_taxonomy: {
    currency: string;
    baseline_monthly_spend: number;
    active_monthly_waste: number;
    potential_monthly_savings: number;
    verified_realized_savings: number;
    anti_double_counting_note: string;
  };
  waste_findings: Array<{
    id: string;
    waste_type: string;
    finding_title: string;
    severity: string;
    status: string;
    assigned_to?: string | null;
    estimated_monthly_waste: number;
    confidence_score: number;
    first_detected_at?: string | null;
  }>;
  recommendations: Array<{
    id: string;
    title: string;
    action_type: string;
    priority: string;
    status: string;
    assigned_to?: string | null;
    estimated_monthly_savings: number;
    revised_monthly_savings?: number | null;
    is_savings_overridden?: boolean;
    risk_level: string;
  }>;
  anomalies: Array<{
    id: string;
    title: string;
    severity: string;
    status: string;
    actual_cost: number;
    expected_cost: number;
    cost_impact: number;
    detected_at?: string | null;
  }>;
  billing_records: Array<{
    id: string;
    charge_period_start?: string | null;
    billed_cost: number;
    effective_cost: number;
    pricing_category?: string;
  }>;
  telemetry_summary: Record<string, MetricSummaryStats>;
  has_telemetry: boolean;
}
