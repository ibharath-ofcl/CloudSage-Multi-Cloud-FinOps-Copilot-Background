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
