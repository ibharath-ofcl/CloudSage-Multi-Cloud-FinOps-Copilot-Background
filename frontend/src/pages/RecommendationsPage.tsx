import React, { useEffect, useState } from 'react';
import { useFilters } from '../context/FilterContext';
import { WorkspaceService } from '../services/api';
import { RecommendationWorkspaceItem } from '../types/workspace';
import { TelemetryPanel } from '../components/TelemetryPanel';
import { RemediationPlaybookPanel } from '../components/RemediationPlaybookPanel';
import { RelatedEvidencePanel } from '../components/RelatedEvidencePanel';
import { AuditTimeline } from '../components/AuditTimeline';
import { BatchReviewToolbar } from '../components/BatchReviewToolbar';
import { ReviewDecisionModal } from '../components/ReviewDecisionModal';
import { SavingsOverrideModal } from '../components/SavingsOverrideModal';

export const RecommendationsPage: React.FC = () => {
  const { filters } = useFilters();
  const [recommendations, setRecommendations] = useState<RecommendationWorkspaceItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  // Search & Filter state
  const [search, setSearch] = useState<string>('');
  const [providerFilter, setProviderFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [priorityFilter, setPriorityFilter] = useState<string>('ALL');
  const [sortBy, setSortBy] = useState<string>('priority');
  const [sortOrder, setSortOrder] = useState<string>('desc');

  // Selection & Batch Review
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [batchAction, setBatchAction] = useState<string | null>(null);

  // Detail Drawer state
  const [selectedRec, setSelectedRec] = useState<RecommendationWorkspaceItem | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'telemetry' | 'playbook' | 'savings' | 'audit'>('overview');

  // Savings Override Modal state
  const [overrideModalRec, setOverrideModalRec] = useState<RecommendationWorkspaceItem | null>(null);

  const loadRecommendations = async () => {
    setLoading(true);
    try {
      const data = await WorkspaceService.listRecommendations({
        provider: providerFilter === 'ALL' ? undefined : providerFilter,
        status: statusFilter === 'ALL' ? undefined : statusFilter,
        priority: priorityFilter === 'ALL' ? undefined : priorityFilter,
        search: search.trim() || undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
        limit: 100,
      });
      setRecommendations(data || []);
      // If active drawer is open, refresh selected recommendation
      if (selectedRec) {
        const updated = (data || []).find((r: RecommendationWorkspaceItem) => r.id === selectedRec.id);
        if (updated) setSelectedRec(updated);
      }
    } catch (err) {
      console.error('Failed to load recommendations', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRecommendations();
  }, [providerFilter, statusFilter, priorityFilter, sortBy, sortOrder]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadRecommendations();
  };

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const selectAll = () => {
    if (selectedIds.length === recommendations.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(recommendations.map((r) => r.id));
    }
  };

  const handleBatchActionSubmit = async (data: {
    reason?: string;
    snoozeDays?: number;
    assignedTo?: string;
    externalTicketRef?: string;
  }) => {
    if (!batchAction) return;
    try {
      await WorkspaceService.batchReviewRecommendations({
        recommendation_ids: selectedIds,
        action: batchAction,
        actor_email: 'finops.lead@enterprise.com',
        reason: data.reason,
        snooze_days: data.snoozeDays,
        assigned_to: data.assignedTo,
        external_ticket_ref: data.externalTicketRef,
      });
      setSelectedIds([]);
      setBatchAction(null);
      await loadRecommendations();
    } catch (err) {
      console.error('Batch review failed', err);
    }
  };

  const handleSingleTransition = async (
    recId: string,
    action: string,
    reason?: string,
    snoozeDays?: number
  ) => {
    try {
      await WorkspaceService.batchReviewRecommendations({
        recommendation_ids: [recId],
        action,
        actor_email: 'finops.lead@enterprise.com',
        reason,
        snooze_days: snoozeDays,
      });
      await loadRecommendations();
    } catch (err) {
      console.error('Status transition failed', err);
    }
  };

  // KPI Calculations
  const totalCount = recommendations.length;
  const totalSavings = recommendations.reduce(
    (sum, r) => sum + (r.revised_monthly_savings != null ? Number(r.revised_monthly_savings) : Number(r.estimated_monthly_savings)),
    0
  );
  const openCount = recommendations.filter(
    (r) => !['DISMISSED', 'REJECTED', 'IMPLEMENTED', 'VERIFIED'].includes(r.status)
  ).length;

  return (
    <div className="p-6 space-y-6">
      {/* Workspace Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-100 tracking-tight">
            Enterprise Recommendation Management Workspace
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Triage, investigate, review, govern savings overrides, and generate multi-cloud remediation playbooks.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={() => loadRecommendations()}
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg border border-slate-700 transition"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="bg-slate-900 p-4 rounded-xl border border-slate-800">
          <div className="text-[11px] font-semibold uppercase text-slate-400">Total In Scope</div>
          <div className="text-2xl font-bold text-slate-100 font-mono mt-1">{totalCount}</div>
        </div>

        <div className="bg-slate-900 p-4 rounded-xl border border-indigo-500/30 bg-indigo-950/20">
          <div className="text-[11px] font-semibold uppercase text-indigo-400">Pending Review</div>
          <div className="text-2xl font-bold text-indigo-300 font-mono mt-1">{openCount}</div>
        </div>

        <div className="bg-slate-900 p-4 rounded-xl border border-emerald-500/30 bg-emerald-950/20">
          <div className="text-[11px] font-semibold uppercase text-emerald-400">Projected Monthly Savings</div>
          <div className="text-2xl font-bold text-emerald-400 font-mono mt-1">${totalSavings.toFixed(2)}</div>
        </div>

        <div className="bg-slate-900 p-4 rounded-xl border border-emerald-500/30 bg-emerald-950/20">
          <div className="text-[11px] font-semibold uppercase text-emerald-400">Annualized Savings</div>
          <div className="text-2xl font-bold text-emerald-400 font-mono mt-1">${(totalSavings * 12).toFixed(2)}</div>
        </div>
      </div>

      {/* Filters & Search Toolbar */}
      <div className="bg-slate-900 p-4 rounded-xl border border-slate-800 flex flex-wrap items-center justify-between gap-3">
        <form onSubmit={handleSearchSubmit} className="flex-1 min-w-[240px]">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by title, resource ID, owner, ticket..."
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </form>

        <div className="flex flex-wrap items-center gap-2">
          {/* Provider Filter */}
          <select
            value={providerFilter}
            onChange={(e) => setProviderFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
          >
            <option value="ALL">All Providers</option>
            <option value="AWS">AWS</option>
            <option value="AZURE">Azure</option>
            <option value="GCP">GCP</option>
          </select>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
          >
            <option value="ALL">All Statuses</option>
            <option value="PROPOSED">Proposed</option>
            <option value="UNDER_REVIEW">Under Review</option>
            <option value="ENDORSED">Endorsed</option>
            <option value="APPROVED">Approved</option>
            <option value="SNOOZED">Snoozed</option>
            <option value="IMPLEMENTED">Implemented</option>
            <option value="VERIFIED">Verified</option>
            <option value="DISMISSED">Dismissed</option>
            <option value="REJECTED">Rejected</option>
          </select>

          {/* Priority Filter */}
          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
          >
            <option value="ALL">All Priorities</option>
            <option value="P1">P1 - Critical</option>
            <option value="P2">P2 - High</option>
            <option value="P3">P3 - Medium</option>
            <option value="P4">P4 - Low</option>
          </select>

          {/* Sort Selector */}
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
          >
            <option value="priority">Sort by Priority</option>
            <option value="savings">Sort by Savings</option>
            <option value="risk">Sort by Risk Score</option>
            <option value="confidence">Sort by Confidence</option>
            <option value="created_at">Sort by Date</option>
          </select>
        </div>
      </div>

      {/* Recommendations Table */}
      <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden shadow-sm">
        {loading ? (
          <div className="p-12 flex items-center justify-center text-slate-400 text-xs">
            <div className="w-5 h-5 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mr-3"></div>
            Loading recommendation workspace...
          </div>
        ) : recommendations.length === 0 ? (
          <div className="p-12 text-center text-slate-500 text-xs">
            No recommendations match your active filters.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/80 text-slate-400 uppercase text-[10px] font-mono border-b border-slate-800">
                <tr>
                  <th className="p-3 w-8">
                    <input
                      type="checkbox"
                      checked={selectedIds.length === recommendations.length && recommendations.length > 0}
                      onChange={selectAll}
                      className="rounded bg-slate-800 border-slate-700 text-indigo-600 focus:ring-0"
                    />
                  </th>
                  <th className="p-3">Recommendation</th>
                  <th className="p-3">Provider</th>
                  <th className="p-3">Priority</th>
                  <th className="p-3">Status</th>
                  <th className="p-3 text-right">Monthly Savings</th>
                  <th className="p-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {recommendations.map((r) => {
                  const isSelected = selectedIds.includes(r.id);
                  const effectiveSavings = r.revised_monthly_savings != null ? r.revised_monthly_savings : r.estimated_monthly_savings;

                  return (
                    <tr
                      key={r.id}
                      className={`hover:bg-slate-800/40 transition ${isSelected ? 'bg-indigo-950/20' : ''}`}
                    >
                      <td className="p-3">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleSelect(r.id)}
                          className="rounded bg-slate-800 border-slate-700 text-indigo-600 focus:ring-0"
                        />
                      </td>

                      <td className="p-3 max-w-sm">
                        <div
                          onClick={() => setSelectedRec(r)}
                          className="font-semibold text-slate-200 hover:text-indigo-400 cursor-pointer truncate"
                        >
                          {r.title}
                        </div>
                        <div className="text-[11px] text-slate-500 truncate mt-0.5">
                          {r.resource_id || r.service_name || 'Account-level'}
                        </div>
                        {r.assigned_to && (
                          <span className="inline-block mt-1 text-[10px] font-mono bg-slate-800 px-1.5 py-0.5 rounded text-slate-400">
                            👤 {r.assigned_to}
                          </span>
                        )}
                      </td>

                      <td className="p-3">
                        <span className="font-mono text-slate-300 font-semibold">{r.provider}</span>
                      </td>

                      <td className="p-3">
                        <span
                          className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                            r.priority === 'P1' || r.priority === 'CRITICAL'
                              ? 'bg-rose-500/20 text-rose-400'
                              : r.priority === 'P2' || r.priority === 'HIGH'
                              ? 'bg-amber-500/20 text-amber-400'
                              : 'bg-blue-500/20 text-blue-400'
                          }`}
                        >
                          {r.priority}
                        </span>
                      </td>

                      <td className="p-3">
                        <span
                          className={`text-[10px] font-semibold px-2 py-0.5 rounded ${
                            r.status === 'APPROVED' || r.status === 'ACCEPTED'
                              ? 'bg-emerald-500/20 text-emerald-400'
                              : r.status === 'SNOOZED'
                              ? 'bg-purple-500/20 text-purple-400'
                              : r.status === 'DISMISSED' || r.status === 'REJECTED'
                              ? 'bg-rose-500/20 text-rose-400'
                              : 'bg-indigo-500/20 text-indigo-400'
                          }`}
                        >
                          {r.status}
                        </span>
                      </td>

                      <td className="p-3 text-right font-mono">
                        <div className="font-bold text-emerald-400">${Number(effectiveSavings).toFixed(2)}</div>
                        {r.is_savings_overridden && (
                          <div className="text-[9px] text-amber-400 font-sans tracking-wide">
                            ★ OVERRIDDEN
                          </div>
                        )}
                      </td>

                      <td className="p-3 text-right">
                        <div className="flex items-center justify-end space-x-1.5">
                          <button
                            onClick={() => setSelectedRec(r)}
                            className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs rounded transition"
                          >
                            Investigate
                          </button>
                          <button
                            onClick={() => handleSingleTransition(r.id, 'APPROVE')}
                            className="px-2 py-1 bg-emerald-600/20 hover:bg-emerald-600/40 text-emerald-300 text-xs rounded transition"
                            title="Approve Recommendation"
                          >
                            ✓
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Slide-over Investigation Drawer */}
      {selectedRec && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-xs">
          <div className="bg-slate-900 border-l border-slate-800 w-full max-w-2xl h-full flex flex-col shadow-2xl animate-in slide-in-from-right duration-200">
            {/* Drawer Header */}
            <div className="p-5 border-b border-slate-800 flex items-start justify-between">
              <div>
                <div className="flex items-center space-x-2">
                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-400 font-mono">
                    {selectedRec.provider}
                  </span>
                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">
                    {selectedRec.action_type}
                  </span>
                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-mono">
                    ${Number(selectedRec.revised_monthly_savings ?? selectedRec.estimated_monthly_savings).toFixed(2)}/mo
                  </span>
                </div>
                <h3 className="text-base font-bold text-slate-100 mt-1">{selectedRec.title}</h3>
                <p className="text-xs text-slate-400 font-mono mt-0.5">{selectedRec.resource_id}</p>
              </div>

              <button
                onClick={() => setSelectedRec(null)}
                className="text-slate-400 hover:text-slate-200 p-1"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Navigation Tabs */}
            <div className="flex border-b border-slate-800 px-5 bg-slate-950/60 text-xs">
              {[
                { id: 'overview', label: 'Overview & Actions' },
                { id: 'telemetry', label: 'Telemetry & Correlations' },
                { id: 'playbook', label: 'Remediation Playbook' },
                { id: 'savings', label: 'Savings Governance' },
                { id: 'audit', label: 'Audit Timeline' },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`py-3 px-3 font-medium border-b-2 transition ${
                    activeTab === tab.id
                      ? 'border-indigo-500 text-indigo-300 font-semibold'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Tab Contents */}
            <div className="flex-1 overflow-y-auto p-5 space-y-4">
              {activeTab === 'overview' && (
                <div className="space-y-4">
                  <div>
                    <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Description</h4>
                    <p className="text-xs text-slate-300 mt-1 leading-relaxed bg-slate-950 p-3 rounded-lg border border-slate-800">
                      {selectedRec.description}
                    </p>
                  </div>

                  <div>
                    <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Remediation Guide</h4>
                    <pre className="text-xs text-slate-300 mt-1 bg-slate-950 p-3 rounded-lg border border-slate-800 font-mono whitespace-pre-wrap">
                      {selectedRec.remediation_guide}
                    </pre>
                  </div>

                  {/* Quick Lifecycle Action Bar */}
                  <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-3">
                    <h4 className="text-xs font-semibold text-slate-300">Human-in-the-Loop Review Controls</h4>
                    <div className="flex flex-wrap gap-2">
                      <button
                        onClick={() => handleSingleTransition(selectedRec.id, 'APPROVE')}
                        className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium rounded-lg transition"
                      >
                        Approve Action
                      </button>
                      <button
                        onClick={() => handleSingleTransition(selectedRec.id, 'SNOOZE', undefined, 14)}
                        className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg transition"
                      >
                        Snooze (14d)
                      </button>
                      <button
                        onClick={() => {
                          const r = prompt('Reason for dismissal:');
                          if (r) handleSingleTransition(selectedRec.id, 'DISMISS', r);
                        }}
                        className="px-3 py-1.5 bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 text-xs font-medium rounded-lg transition"
                      >
                        Dismiss
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {activeTab === 'telemetry' && (
                <div className="space-y-4">
                  <TelemetryPanel recommendationId={selectedRec.id} resourceId={selectedRec.resource_id} />
                  <RelatedEvidencePanel recommendationId={selectedRec.id} resourceId={selectedRec.resource_id || undefined} />
                </div>
              )}

              {activeTab === 'playbook' && (
                <RemediationPlaybookPanel recommendationId={selectedRec.id} />
              )}

              {activeTab === 'savings' && (
                <div className="space-y-4">
                  <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 flex items-center justify-between">
                    <div>
                      <div className="text-xs text-slate-400">Current Active Savings Baseline</div>
                      <div className="text-lg font-bold text-emerald-400 font-mono">
                        ${Number(selectedRec.revised_monthly_savings ?? selectedRec.estimated_monthly_savings).toFixed(2)} USD/mo
                      </div>
                      {selectedRec.is_savings_overridden && (
                        <div className="text-[10px] text-amber-400 mt-0.5">
                          Approved via Governance Override
                        </div>
                      )}
                    </div>
                    <button
                      onClick={() => setOverrideModalRec(selectedRec)}
                      className="px-3 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg transition"
                    >
                      Propose Revised Savings
                    </button>
                  </div>

                  <RelatedEvidencePanel recommendationId={selectedRec.id} />
                </div>
              )}

              {activeTab === 'audit' && (
                <AuditTimeline historyItems={selectedRec.history_items || []} />
              )}
            </div>
          </div>
        </div>
      )}

      {/* Batch Review Action Floating Toolbar */}
      <BatchReviewToolbar
        selectedCount={selectedIds.length}
        onClearSelection={() => setSelectedIds([])}
        onAction={(act) => setBatchAction(act)}
      />

      {/* Review Decision Modal */}
      <ReviewDecisionModal
        isOpen={batchAction !== null}
        action={batchAction || 'APPROVE'}
        itemCount={selectedIds.length}
        onClose={() => setBatchAction(null)}
        onSubmit={handleBatchActionSubmit}
      />

      {/* Savings Override Modal */}
      {overrideModalRec && (
        <SavingsOverrideModal
          isOpen={overrideModalRec !== null}
          recommendationId={overrideModalRec.id}
          currentSavings={Number(overrideModalRec.estimated_monthly_savings)}
          onClose={() => setOverrideModalRec(null)}
          onSuccess={() => {
            setOverrideModalRec(null);
            loadRecommendations();
          }}
        />
      )}
    </div>
  );
};
