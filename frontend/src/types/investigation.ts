/**
 * CloudSage Investigation Workspace & Root Cause Analysis TypeScript Definitions.
 * Aligned with backend/app/schemas/investigation.py.
 */

export type InvestigationLifecycleStatus =
  | 'NEW'
  | 'ASSIGNED'
  | 'INVESTIGATING'
  | 'ROOT_CAUSE_IDENTIFIED'
  | 'ACTION_RECOMMENDED'
  | 'RESOLVED'
  | 'CLOSED';

export type InvestigationPriorityTier = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export type FindingType = 'FACT' | 'CORRELATION' | 'HYPOTHESIS' | 'VERIFIED_CAUSE';

export type ConfidenceCategory = 'HIGH' | 'MEDIUM' | 'LOW' | 'INSUFFICIENT_EVIDENCE';

export interface InvestigationCase {
  id: string;
  case_number: string;
  anomaly_id: string;
  alert_instance_id?: string | null;
  title: string;
  status: InvestigationLifecycleStatus;
  priority: InvestigationPriorityTier;
  assigned_to?: string | null;
  assigned_at?: string | null;
  provider: 'AWS' | 'AZURE' | 'GCP';
  account_id: string;
  service_name: string;
  region?: string | null;
  resource_id?: string | null;
  excess_cost: number;
  actual_cost: number;
  expected_cost: number;
  root_cause_summary?: string | null;
  verified_root_cause?: string | null;
  suspected_category?: string | null;
  resolution_notes?: string | null;
  created_by: string;
  updated_by?: string | null;
  created_at: string;
  updated_at: string;
  closed_at?: string | null;
  closed_by?: string | null;
}

export interface InvestigationFinding {
  id: string;
  investigation_id: string;
  finding_type: FindingType;
  title: string;
  explanation: string;
  dimension?: string | null;
  financial_impact: number;
  contribution_percentage: number;
  confidence_category: ConfidenceCategory;
  confidence_score: number;
  evidence_source: string;
  evidence_reference?: string | null;
  supporting_observations: string[];
  contradictory_observations: string[];
  suggested_next_step?: string | null;
  created_by: string;
  created_at: string;
}

export interface InvestigationNote {
  id: string;
  investigation_id: string;
  author: string;
  content: string;
  is_system_generated: boolean;
  created_at: string;
}

export interface InvestigationEvidenceLink {
  id: string;
  investigation_id: string;
  entity_type: string;
  entity_id: string;
  relationship_role: string;
  metadata_snapshot: Record<string, any>;
  created_at: string;
}

export interface InvestigationHistory {
  id: string;
  investigation_id: string;
  from_status?: string | null;
  to_status: string;
  actor: string;
  action: string;
  notes?: string | null;
  details: Record<string, any>;
  created_at: string;
}

export interface InvestigationCaseDetail extends InvestigationCase {
  findings: InvestigationFinding[];
  notes: InvestigationNote[];
  evidence_links: InvestigationEvidenceLink[];
  history: InvestigationHistory[];
  anomaly_details?: Record<string, any> | null;
}

export interface InvestigationCaseListResponse {
  items: InvestigationCase[];
  total: number;
}

export interface InvestigationStats {
  total_investigations: number;
  open_investigations: number;
  critical_investigations: number;
  unassigned_investigations: number;
  root_cause_identified_count: number;
  resolved_investigations: number;
  total_excess_spend_investigated: number;
  average_investigation_age_hours: number;
}

export interface DimensionContributor {
  dimension_key: string;
  dimension_value: string;
  actual_cost: number;
  expected_cost: number;
  excess_cost: number;
  percentage_deviation: number;
  contribution_share: number;
  resource_count: number;
}

export interface MultiDimensionalAnalysis {
  investigation_id: string;
  anomaly_id: string;
  total_excess_cost: number;
  dimensions: Record<string, DimensionContributor[]>;
  dominant_dimension: string;
  analysis_timestamp: string;
}

export interface ContributionRankingItem {
  rank: number;
  entity_type: string;
  entity_id: string;
  entity_name?: string | null;
  provider: string;
  service_name: string;
  excess_cost: number;
  contribution_share: number;
  cumulative_share: number;
  confidence_category: ConfidenceCategory;
}

export interface ContributionRankingResponse {
  investigation_id: string;
  total_excess_cost: number;
  top_contributors: ContributionRankingItem[];
  pareto_80_count: number;
}

export interface UsagePriceDecompositionItem {
  category: string;
  amount: number;
  percentage_share: number;
  explanation: string;
}

export interface UsagePriceAnalysis {
  investigation_id: string;
  total_excess_cost: number;
  usage_effect: number;
  price_effect: number;
  mix_or_quantity_effect: number;
  unclassified_effect: number;
  primary_cost_driver: string;
  decomposition_breakdown: UsagePriceDecompositionItem[];
  methodology_notes: string;
}

export interface TimelineDataPoint {
  date: string;
  actual_cost: number;
  baseline_expected_cost: number;
  excess_cost: number;
  is_anomaly_period: boolean;
  seven_day_moving_avg?: number | null;
}

export interface TimelineAnalysis {
  investigation_id: string;
  anomaly_date: string;
  anomaly_start: string;
  peak_spend_date: string;
  peak_excess_cost: number;
  data_points: TimelineDataPoint[];
  day_over_day_change_pct: number;
  week_over_week_change_pct: number;
  month_over_month_change_pct: number;
}

export interface ResourceInvestigationItem {
  resource_id: string;
  resource_name?: string | null;
  resource_type: string;
  provider: string;
  region: string;
  owner?: string | null;
  environment: string;
  cost_center?: string | null;
  actual_cost: number;
  excess_cost: number;
  contribution_percentage: number;
  status: string;
  metrics_summary: Record<string, any>;
  relationships: Array<{
    source: string;
    target: string;
    type: string;
    confidence: number;
  }>;
}

export interface ResourceInvestigationResponse {
  investigation_id: string;
  total_affected_resources: number;
  resources: ResourceInvestigationItem[];
}

export interface CrossSignalCorrelation {
  investigation_id: string;
  correlated_waste_detections: Array<{
    id: string;
    rule_name: string;
    waste_type: string;
    wasted_cost: number;
    severity: string;
    status: string;
  }>;
  correlated_recommendations: Array<{
    id: string;
    title: string;
    strategy: string;
    estimated_monthly_savings: number;
    priority: string;
    status: string;
  }>;
  correlated_alerts: Array<{
    id: string;
    rule_name: string;
    severity: string;
    status: string;
    trigger_value: number;
  }>;
  correlation_confidence: ConfidenceCategory;
  correlation_summary: string;
}
