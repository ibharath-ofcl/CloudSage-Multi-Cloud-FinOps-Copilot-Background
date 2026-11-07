/**
 * CloudSage Multi-Cloud FinOps Copilot - Dashboard TypeScript Type Definitions.
 * Aligned with backend/app/schemas/dashboard.py.
 */

export interface DashboardFilterParams {
  startDate?: string | null;
  endDate?: string | null;
  provider?: 'AWS' | 'AZURE' | 'GCP' | 'ALL';
  service?: string | null;
  accountId?: string | null;
  region?: string | null;
  environment?: string | null;
  owner?: string | null;
  costCenter?: string | null;
}

export interface KpiCardData {
  title: string;
  value: string;
  rawAmount: number;
  currency: string;
  changePct?: number | null;
  trend: 'UP' | 'DOWN' | 'NEUTRAL';
  subtitle?: string | null;
  isPositiveGood?: boolean;
}

export interface ExecutiveKpiSummary {
  currency: string;
  totalSpend: string;
  totalSpendAmount: number;
  monthToDateSpend: string;
  monthToDateAmount: number;
  momChangePct: number;
  forecastedMonthlySpend: string;
  forecastedMonthlyAmount: number;
  detectedWaste: string;
  detectedWasteAmount: number;
  wastePercentageOfSpend: number;
  anomalyImpact: string;
  anomalyImpactAmount: number;
  activeAnomalyCount: number;
  potentialSavings: string;
  potentialSavingsAmount: number;
  realizedSavings: string;
  realizedSavingsAmount: number;
  activeRecommendationsCount: number;
  dataQualityScore: number;
  totalTrackedResources: number;
}

export interface ProviderBreakdownItem {
  provider: string;
  spend: string;
  amount: number;
  percentage: number;
  resourceCount: number;
  wasteAmount: number;
  anomalyCount: number;
  currency: string;
}

export interface DailySpendPoint {
  date: string;
  total: number;
  aws: number;
  azure: number;
  gcp: number;
}

export interface ServiceSpendItem {
  service: string;
  provider: string;
  spend: string;
  amount: number;
  percentage: number;
  resourceCount: number;
}

export interface AnomalyCardItem {
  id: string;
  provider: string;
  service: string;
  severity: string;
  status: string;
  detectedCost: string;
  expectedCost: string;
  deviationScore: number;
  detectedDate: string;
  explanation: string;
}

export interface WasteCardItem {
  id: string;
  provider: string;
  resourceId: string;
  wasteType: string;
  severity: string;
  status: string;
  estimatedMonthlyWaste: string;
  owner?: string | null;
  recommendationSnippet: string;
}

export interface RecommendationCardItem {
  id: string;
  provider: string;
  category: string;
  priority: string;
  action: string;
  estimatedMonthlySavings: string;
  effort: string;
  status: string;
}

export interface DashboardOverviewResponse {
  kpis: ExecutiveKpiSummary;
  providerBreakdown: ProviderBreakdownItem[];
  recentSpendTrend: DailySpendPoint[];
  topServices: ServiceSpendItem[];
  recentAnomalies: AnomalyCardItem[];
  topWasteFindings: WasteCardItem[];
  highImpactRecommendations: RecommendationCardItem[];
  generatedAt: string;
}

export interface CostTrendResponse {
  granularity: 'DAILY' | 'MONTHLY';
  currency: string;
  totalSpend: string;
  points: DailySpendPoint[];
}

export interface ProviderComparisonResponse {
  currency: string;
  totalSpend: string;
  providers: ProviderBreakdownItem[];
  topServicesByProvider: Record<string, ServiceSpendItem[]>;
}

export interface ServiceBreakdownResponse {
  currency: string;
  totalSpend: string;
  services: ServiceSpendItem[];
}

export interface AnomalySummaryResponse {
  currency: string;
  totalAnomaliesCount: number;
  activeAnomaliesCount: number;
  resolvedAnomaliesCount: number;
  totalFinancialImpact: string;
  bySeverity: Record<string, number>;
  byProvider: Record<string, number>;
  recentAnomalies: AnomalyCardItem[];
}

export interface WasteSummaryResponse {
  currency: string;
  totalFindingsCount: number;
  openFindingsCount: number;
  totalMonthlyWaste: string;
  totalAnnualWaste: string;
  byCategory: Record<string, number>;
  byProvider: Record<string, number>;
  topFindings: WasteCardItem[];
}

export interface RecommendationSummaryResponse {
  currency: string;
  totalRecommendationsCount: number;
  openRecommendationsCount: number;
  totalMonthlySavings: string;
  totalAnnualSavings: string;
  byPriority: Record<string, number>;
  byCategory: Record<string, number>;
  byEffort: Record<string, number>;
  topRecommendations: RecommendationCardItem[];
}

export interface SavingsSummaryResponse {
  currency: string;
  potentialMonthlySavings: string;
  potentialAnnualSavings: string;
  realizedMonthlySavings: string;
  realizedAnnualSavings: string;
  realizationRatePct: number;
  savingsByProvider: Record<string, string>;
  savingsByCategory: Record<string, string>;
}

export interface InventorySummaryResponse {
  totalResources: number;
  byProvider: Record<string, number>;
  byStatus: Record<string, number>;
  unattachedCount: number;
  taggedPercentage: number;
  lastSyncTimestamp?: string | null;
}

export interface DataQualitySummaryResponse {
  overallQualityScore: number;
  focusComplianceScore: number;
  tagCoverageScore: number;
  missingTagCount: number;
  validationWarnings: number;
  lastValidationTimestamp?: string | null;
}

export interface CopilotChatResponse {
  conversation_id: string;
  role: string;
  content: string;
  confidence: number;
  suggested_follow_ups: string[];
}
