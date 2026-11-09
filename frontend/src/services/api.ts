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
import {
  AlertRule,
  AlertRuleCreate,
  AlertRuleUpdate,
  AlertRuleListResponse,
  AlertRulePreviewRequest,
  AlertRulePreviewResponse,
  AlertInstance,
  AlertInstanceListResponse,
  AlertInstanceDetail,
  AlertStats,
  AlertActionRequest,
  AlertHistory,
  InAppNotification,
  InAppNotificationListResponse,
  UnreadCountResponse,
  NotificationOutbox,
  NotificationOutboxListResponse,
  NotificationHealth,
  NotificationPreference,
} from '../types/alerts';
import {
  InvestigationCase,
  InvestigationCaseDetail,
  InvestigationCaseListResponse,
  InvestigationFinding,
  InvestigationNote,
  InvestigationEvidenceLink,
  InvestigationHistory,
  InvestigationStats,
  MultiDimensionalAnalysis,
  ContributionRankingResponse,
  UsagePriceAnalysis,
  TimelineAnalysis,
  ResourceInvestigationResponse,
  CrossSignalCorrelation,
} from '../types/investigation';

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

export const AlertService = {
  async listRules(params?: {
    provider?: string;
    severity?: string;
    is_active?: boolean;
    search?: string;
    limit?: number;
    offset?: number;
  }): Promise<AlertRuleListResponse> {
    const res = await apiClient.get<AlertRuleListResponse>('/alert-rules', { params });
    return res.data;
  },

  async getRule(ruleId: string): Promise<AlertRule> {
    const res = await apiClient.get<AlertRule>(`/alert-rules/${ruleId}`);
    return res.data;
  },

  async createRule(rule: AlertRuleCreate): Promise<AlertRule> {
    const res = await apiClient.post<AlertRule>('/alert-rules', rule);
    return res.data;
  },

  async updateRule(ruleId: string, rule: AlertRuleUpdate): Promise<AlertRule> {
    const res = await apiClient.put<AlertRule>(`/alert-rules/${ruleId}`, rule);
    return res.data;
  },

  async toggleRule(ruleId: string): Promise<AlertRule> {
    const res = await apiClient.post<AlertRule>(`/alert-rules/${ruleId}/toggle`);
    return res.data;
  },

  async deleteRule(ruleId: string): Promise<{ status: string; rule_id: string }> {
    const res = await apiClient.delete<{ status: string; rule_id: string }>(`/alert-rules/${ruleId}`);
    return res.data;
  },

  async previewRule(previewData: AlertRulePreviewRequest): Promise<AlertRulePreviewResponse> {
    const res = await apiClient.post<AlertRulePreviewResponse>('/alert-rules/preview', previewData);
    return res.data;
  },

  async listAlerts(params?: {
    status?: string;
    severity?: string;
    provider?: string;
    rule_id?: string;
    is_suppressed?: boolean;
    start_date?: string;
    end_date?: string;
    search?: string;
    limit?: number;
    offset?: number;
  }): Promise<AlertInstanceListResponse> {
    const res = await apiClient.get<AlertInstanceListResponse>('/alerts', { params });
    return res.data;
  },

  async getStats(): Promise<AlertStats> {
    const res = await apiClient.get<AlertStats>('/alerts/stats');
    return res.data;
  },

  async getAlert(alertId: string): Promise<AlertInstanceDetail> {
    const res = await apiClient.get<AlertInstanceDetail>(`/alerts/${alertId}`);
    return res.data;
  },

  async executeAction(alertId: string, actionData: AlertActionRequest): Promise<AlertInstance> {
    const res = await apiClient.post<AlertInstance>(`/alerts/${alertId}/action`, actionData);
    return res.data;
  },

  async getAlertHistory(alertId: string): Promise<AlertHistory[]> {
    const res = await apiClient.get<AlertHistory[]>(`/alerts/${alertId}/history`);
    return res.data;
  },
};

export const NotificationService = {
  async listNotifications(params?: {
    unread_only?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<InAppNotificationListResponse> {
    const res = await apiClient.get<InAppNotificationListResponse>('/notifications', { params });
    return res.data;
  },

  async getUnreadCount(): Promise<UnreadCountResponse> {
    const res = await apiClient.get<UnreadCountResponse>('/notifications/unread-count');
    return res.data;
  },

  async markAsRead(notificationId: string): Promise<InAppNotification> {
    const res = await apiClient.post<InAppNotification>(`/notifications/${notificationId}/read`);
    return res.data;
  },

  async markAsUnread(notificationId: string): Promise<InAppNotification> {
    const res = await apiClient.post<InAppNotification>(`/notifications/${notificationId}/unread`);
    return res.data;
  },

  async markAllAsRead(): Promise<{ status: string; marked_read_count: number }> {
    const res = await apiClient.post<{ status: string; marked_read_count: number }>('/notifications/mark-all-read');
    return res.data;
  },

  async listOutbox(params?: {
    status?: string;
    channel?: string;
    limit?: number;
    offset?: number;
  }): Promise<NotificationOutboxListResponse> {
    const res = await apiClient.get<NotificationOutboxListResponse>('/notification-deliveries/outbox', { params });
    return res.data;
  },

  async getOutboxItem(outboxId: string): Promise<NotificationOutbox> {
    const res = await apiClient.get<NotificationOutbox>(`/notification-deliveries/outbox/${outboxId}`);
    return res.data;
  },

  async retryOutbox(outboxId: string): Promise<any> {
    const res = await apiClient.post(`/notification-deliveries/outbox/${outboxId}/retry`);
    return res.data;
  },

  async cancelOutbox(outboxId: string): Promise<NotificationOutbox> {
    const res = await apiClient.post<NotificationOutbox>(`/notification-deliveries/outbox/${outboxId}/cancel`);
    return res.data;
  },

  async getPipelineHealth(): Promise<NotificationHealth> {
    const res = await apiClient.get<NotificationHealth>('/notification-deliveries/health');
    return res.data;
  },

  async dispatchOutbox(batchSize: number = 50): Promise<any> {
    const res = await apiClient.post('/notification-deliveries/dispatch', null, {
      params: { batch_size: batchSize },
    });
    return res.data;
  },

  async getPreferences(): Promise<NotificationPreference> {
    const res = await apiClient.get<NotificationPreference>('/notification-preferences/me');
    return res.data;
  },

  async updatePreferences(pref: Partial<NotificationPreference>): Promise<NotificationPreference> {
    const res = await apiClient.put<NotificationPreference>('/notification-preferences/me', pref);
    return res.data;
  },
};

export const InvestigationService = {
  async getStats(): Promise<InvestigationStats> {
    const res = await apiClient.get<InvestigationStats>('/investigations/stats');
    return res.data;
  },

  async listInvestigations(params?: {
    provider?: string;
    status?: string;
    priority?: string;
    assigned_to?: string;
    service_name?: string;
    search?: string;
    limit?: number;
    offset?: number;
  }): Promise<InvestigationCaseListResponse> {
    const res = await apiClient.get<InvestigationCaseListResponse>('/investigations', { params });
    return res.data;
  },

  async createInvestigation(payload: {
    anomaly_id: string;
    alert_instance_id?: string;
    title?: string;
    priority?: string;
    assigned_to?: string;
    initial_notes?: string;
  }): Promise<InvestigationCaseDetail> {
    const res = await apiClient.post<InvestigationCaseDetail>('/investigations', payload);
    return res.data;
  },

  async getInvestigationDetail(investigationId: string): Promise<InvestigationCaseDetail> {
    const res = await apiClient.get<InvestigationCaseDetail>(`/investigations/${investigationId}`);
    return res.data;
  },

  async updateInvestigation(
    investigationId: string,
    payload: {
      title?: string;
      priority?: string;
      assigned_to?: string;
      root_cause_summary?: string;
      verified_root_cause?: string;
      suspected_category?: string;
      resolution_notes?: string;
    }
  ): Promise<InvestigationCaseDetail> {
    const res = await apiClient.put<InvestigationCaseDetail>(`/investigations/${investigationId}`, payload);
    return res.data;
  },

  async assignCase(
    investigationId: string,
    assignedTo: string,
    notes?: string
  ): Promise<InvestigationCaseDetail> {
    const res = await apiClient.post<InvestigationCaseDetail>(`/investigations/${investigationId}/assign`, {
      assigned_to: assignedTo,
      notes,
    });
    return res.data;
  },

  async transitionStatus(
    investigationId: string,
    targetStatus: string,
    notes?: string,
    verifiedRootCause?: string
  ): Promise<InvestigationCaseDetail> {
    const res = await apiClient.post<InvestigationCaseDetail>(`/investigations/${investigationId}/transition`, {
      status: targetStatus,
      notes,
      verified_root_cause: verifiedRootCause,
    });
    return res.data;
  },

  async closeCase(investigationId: string, notes?: string): Promise<InvestigationCaseDetail> {
    const res = await apiClient.post<InvestigationCaseDetail>(`/investigations/${investigationId}/close`, null, {
      params: { notes },
    });
    return res.data;
  },

  async reopenCase(investigationId: string, notes?: string): Promise<InvestigationCaseDetail> {
    const res = await apiClient.post<InvestigationCaseDetail>(`/investigations/${investigationId}/reopen`, null, {
      params: { notes },
    });
    return res.data;
  },

  async getDimensions(investigationId: string): Promise<MultiDimensionalAnalysis> {
    const res = await apiClient.get<MultiDimensionalAnalysis>(`/investigations/${investigationId}/dimensions`);
    return res.data;
  },

  async getContributions(investigationId: string): Promise<ContributionRankingResponse> {
    const res = await apiClient.get<ContributionRankingResponse>(`/investigations/${investigationId}/contributions`);
    return res.data;
  },

  async getUsagePriceAnalysis(investigationId: string): Promise<UsagePriceAnalysis> {
    const res = await apiClient.get<UsagePriceAnalysis>(`/investigations/${investigationId}/usage-price-analysis`);
    return res.data;
  },

  async getTimeline(investigationId: string): Promise<TimelineAnalysis> {
    const res = await apiClient.get<TimelineAnalysis>(`/investigations/${investigationId}/timeline`);
    return res.data;
  },

  async getResources(investigationId: string): Promise<ResourceInvestigationResponse> {
    const res = await apiClient.get<ResourceInvestigationResponse>(`/investigations/${investigationId}/resources`);
    return res.data;
  },

  async getCorrelations(investigationId: string): Promise<CrossSignalCorrelation> {
    const res = await apiClient.get<CrossSignalCorrelation>(`/investigations/${investigationId}/correlations`);
    return res.data;
  },

  async getRootCauses(investigationId: string): Promise<InvestigationFinding[]> {
    const res = await apiClient.get<InvestigationFinding[]>(`/investigations/${investigationId}/root-causes`);
    return res.data;
  },

  async getEvidence(investigationId: string): Promise<InvestigationEvidenceLink[]> {
    const res = await apiClient.get<InvestigationEvidenceLink[]>(`/investigations/${investigationId}/evidence`);
    return res.data;
  },

  async addNote(investigationId: string, content: string): Promise<InvestigationNote> {
    const res = await apiClient.post<InvestigationNote>(`/investigations/${investigationId}/notes`, { content });
    return res.data;
  },

  async addFinding(investigationId: string, finding: Partial<InvestigationFinding>): Promise<InvestigationFinding> {
    const res = await apiClient.post<InvestigationFinding>(`/investigations/${investigationId}/findings`, finding);
    return res.data;
  },

  async getHistory(investigationId: string): Promise<InvestigationHistory[]> {
    const res = await apiClient.get<InvestigationHistory[]>(`/investigations/${investigationId}/history`);
    return res.data;
  },

  async investigateAnomaly(anomalyId: string): Promise<InvestigationCaseDetail> {
    const res = await apiClient.post<InvestigationCaseDetail>(`/anomalies/${anomalyId}/investigate`);
    return res.data;
  },

  async getAnomalySummary(anomalyId: string): Promise<any> {
    const res = await apiClient.get(`/anomalies/${anomalyId}/investigation-summary`);
    return res.data;
  },
};
