/**
 * CloudSage Multi-Cloud FinOps Copilot - Frontend API Client.
 * Communicates with backend FastAPI endpoints.
 */

import axios from 'axios';
import {
  DashboardFilterParams,
  DashboardOverviewResponse,
  CostTrendResponse,
  ProviderComparisonResponse,
  ServiceBreakdownResponse,
  AnomalySummaryResponse,
  WasteSummaryResponse,
  RecommendationSummaryResponse,
  SavingsSummaryResponse,
  InventorySummaryResponse,
  DataQualitySummaryResponse,
  CopilotChatResponse,
} from '../types/dashboard';

const API_BASE = '/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

function formatParams(params?: DashboardFilterParams): Record<string, string> {
  if (!params) return {};
  const query: Record<string, string> = {};
  if (params.startDate) query.start_date = params.startDate;
  if (params.endDate) query.end_date = params.endDate;
  if (params.provider && params.provider !== 'ALL') query.provider = params.provider;
  if (params.service) query.service = params.service;
  if (params.accountId) query.account_id = params.accountId;
  if (params.region) query.region = params.region;
  if (params.environment) query.environment = params.environment;
  if (params.owner) query.owner = params.owner;
  if (params.costCenter) query.cost_center = params.costCenter;
  return query;
}

export const DashboardService = {
  async getOverview(params?: DashboardFilterParams): Promise<DashboardOverviewResponse> {
    const res = await apiClient.get<DashboardOverviewResponse>('/dashboard/overview', {
      params: formatParams(params),
    });
    return res.data;
  },

  async getKpis(params?: DashboardFilterParams) {
    const res = await apiClient.get('/dashboard/kpis', {
      params: formatParams(params),
    });
    return res.data;
  },

  async getCostTrends(params?: DashboardFilterParams, granularity: 'DAILY' | 'MONTHLY' = 'DAILY'): Promise<CostTrendResponse> {
    const res = await apiClient.get<CostTrendResponse>('/dashboard/trends', {
      params: { ...formatParams(params), granularity },
    });
    return res.data;
  },

  async getProviderComparison(params?: DashboardFilterParams): Promise<ProviderComparisonResponse> {
    const res = await apiClient.get<ProviderComparisonResponse>('/dashboard/provider-comparison', {
      params: formatParams(params),
    });
    return res.data;
  },

  async getServiceBreakdown(params?: DashboardFilterParams): Promise<ServiceBreakdownResponse> {
    const res = await apiClient.get<ServiceBreakdownResponse>('/dashboard/service-breakdown', {
      params: formatParams(params),
    });
    return res.data;
  },

  async getAnomalySummary(params?: DashboardFilterParams): Promise<AnomalySummaryResponse> {
    const res = await apiClient.get<AnomalySummaryResponse>('/dashboard/anomalies', {
      params: formatParams(params),
    });
    return res.data;
  },

  async getWasteSummary(params?: DashboardFilterParams): Promise<WasteSummaryResponse> {
    const res = await apiClient.get<WasteSummaryResponse>('/dashboard/waste', {
      params: formatParams(params),
    });
    return res.data;
  },

  async getRecommendationSummary(params?: DashboardFilterParams): Promise<RecommendationSummaryResponse> {
    const res = await apiClient.get<RecommendationSummaryResponse>('/dashboard/recommendations', {
      params: formatParams(params),
    });
    return res.data;
  },

  async getSavingsSummary(params?: DashboardFilterParams): Promise<SavingsSummaryResponse> {
    const res = await apiClient.get<SavingsSummaryResponse>('/dashboard/savings', {
      params: formatParams(params),
    });
    return res.data;
  },

  async getInventorySummary(params?: DashboardFilterParams): Promise<InventorySummaryResponse> {
    const res = await apiClient.get<InventorySummaryResponse>('/dashboard/inventory', {
      params: formatParams(params),
    });
    return res.data;
  },

  async getDataQualitySummary(params?: DashboardFilterParams): Promise<DataQualitySummaryResponse> {
    const res = await apiClient.get<DataQualitySummaryResponse>('/dashboard/data-quality', {
      params: formatParams(params),
    });
    return res.data;
  },

  getExportUrl(format: 'CSV' | 'JSON', section: string, params?: DashboardFilterParams): string {
    const query = new URLSearchParams({
      format: format.toLowerCase(),
      section,
      ...formatParams(params),
    });
    return `${API_BASE}/dashboard/export?${query.toString()}`;
  },
};

export const CopilotService = {
  async askQuestion(query: string, conversationId?: string, userId: string = 'dashboard_user'): Promise<CopilotChatResponse> {
    const res = await apiClient.post<CopilotChatResponse>('/copilot/chat', {
      query,
      conversation_id: conversationId,
      user_id: userId,
    });
    return res.data;
  },

  async getCapabilities() {
    const res = await apiClient.get('/copilot/capabilities');
    return res.data;
  },
};

export const WorkspaceService = {
  // Recommendations
  async listRecommendations(params?: {
    provider?: string;
    status?: string;
    priority?: string;
    risk_level?: string;
    action_type?: string;
    assigned_to?: string;
    min_savings?: number;
    search?: string;
    sort_by?: string;
    sort_order?: string;
    skip?: number;
    limit?: number;
  }) {
    const res = await apiClient.get('/recommendations', { params });
    return res.data;
  },

  async getRecommendation(recId: string) {
    const res = await apiClient.get(`/recommendations/${recId}`);
    return res.data;
  },

  async updateRecommendationStatus(recId: string, payload: {
    status: string;
    actor_email: string;
    reason?: string;
    notes?: string;
  }) {
    const res = await apiClient.patch(`/recommendations/${recId}/status`, payload);
    return res.data;
  },

  async batchReviewRecommendations(payload: {
    recommendation_ids: string[];
    action: string;
    actor_email: string;
    reason?: string;
    snooze_days?: number;
    assigned_to?: string;
    external_ticket_ref?: string;
  }) {
    const res = await apiClient.post('/recommendations/batch', payload);
    return res.data;
  },

  async proposeSavingsOverride(recId: string, payload: {
    proposed_monthly_savings: number;
    reason: string;
    proposed_by: string;
  }) {
    const res = await apiClient.post(`/recommendations/${recId}/override`, payload);
    return res.data;
  },

  async listSavingsOverrides(recId: string) {
    const res = await apiClient.get(`/recommendations/${recId}/overrides`);
    return res.data;
  },

  async approveSavingsOverride(recId: string, overrideId: string, payload: {
    approved: boolean;
    approved_by: string;
    rejection_reason?: string;
  }) {
    const res = await apiClient.post(`/recommendations/${recId}/override/${overrideId}/approve`, payload);
    return res.data;
  },

  async getRecommendationPlaybook(recId: string, format: string = 'markdown') {
    const res = await apiClient.get(`/recommendations/${recId}/playbook`, { params: { format } });
    return res.data;
  },

  getRecommendationPlaybookDownloadUrl(recId: string, format: string = 'markdown') {
    return `${API_BASE}/recommendations/${recId}/playbook/download?format=${format}`;
  },

  async getRecommendationTelemetry(recId: string, days: number = 14) {
    const res = await apiClient.get(`/recommendations/${recId}/telemetry`, { params: { days } });
    return res.data;
  },

  async getRecommendationCorrelations(recId: string) {
    const res = await apiClient.get(`/recommendations/${recId}/correlations`);
    return res.data;
  },

  // Waste Findings
  async listWasteFindings(params?: {
    provider?: string;
    account_id?: string;
    waste_type?: string;
    severity?: string;
    status?: string;
    min_savings?: number;
    owner?: string;
    environment?: string;
    limit?: number;
    offset?: number;
  }) {
    const res = await apiClient.get('/waste-detection/findings', { params });
    return res.data;
  },

  async getWasteFinding(findingId: string) {
    const res = await apiClient.get(`/waste-detection/findings/${findingId}`);
    return res.data;
  },

  async performWasteAction(findingId: string, payload: {
    action: string;
    actor: string;
    reason?: string;
    snooze_days?: number;
    assigned_to?: string;
  }) {
    const res = await apiClient.post(`/waste-detection/findings/${findingId}/action`, payload);
    return res.data;
  },

  async batchWasteAction(payload: {
    finding_ids: string[];
    action: string;
    actor: string;
    reason?: string;
    snooze_days?: number;
    assigned_to?: string;
  }) {
    const res = await apiClient.post('/waste-detection/batch', payload);
    return res.data;
  },

  async getFindingPlaybook(findingId: string, format: string = 'markdown') {
    const res = await apiClient.get(`/waste-detection/findings/${findingId}/playbook`, { params: { format } });
    return res.data;
  },

  getFindingPlaybookDownloadUrl(findingId: string, format: string = 'markdown') {
    return `${API_BASE}/waste-detection/findings/${findingId}/playbook/download?format=${format}`;
  },

  async getFindingTelemetry(findingId: string, days: number = 14) {
    const res = await apiClient.get(`/waste-detection/findings/${findingId}/telemetry`, { params: { days } });
    return res.data;
  },

  async getFindingInvestigation(findingId: string) {
    const res = await apiClient.get(`/waste-detection/findings/${findingId}/investigation`);
    return res.data;
  },

  // General Inventory Resource Telemetry & Correlations
  async getResourceTelemetry(resourceId: string, days: number = 14) {
    const res = await apiClient.get(`/inventory/resources/${encodeURIComponent(resourceId)}/telemetry`, { params: { days } });
    return res.data;
  },

  async getResourceCorrelations(resourceId: string) {
    const res = await apiClient.get(`/inventory/resources/${encodeURIComponent(resourceId)}/correlations`);
    return res.data;
  },
};
