import React, { useEffect, useState } from 'react';
import { useFilters } from '../context/FilterContext';
import { WorkspaceService } from '../services/api';
import { WasteFindingWorkspaceItem } from '../types/workspace';
import { TelemetryPanel } from '../components/TelemetryPanel';
import { RemediationPlaybookPanel } from '../components/RemediationPlaybookPanel';
import { RelatedEvidencePanel } from '../components/RelatedEvidencePanel';
import { BatchReviewToolbar } from '../components/BatchReviewToolbar';
import { ReviewDecisionModal } from '../components/ReviewDecisionModal';

export const WastePage: React.FC = () => {
  const { filters } = useFilters();
  const [findings, setFindings] = useState<WasteFindingWorkspaceItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  // Filters
  const [providerFilter, setProviderFilter] = useState<string>('ALL');
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [wasteTypeFilter, setWasteTypeFilter] = useState<string>('ALL');

  // Selection & Batch
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [batchAction, setBatchAction] = useState<string | null>(null);

  // Drawer
  const [selectedFinding, setSelectedFinding] = useState<WasteFindingWorkspaceItem | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'telemetry' | 'playbook' | 'correlations'>('overview');

  const loadFindings = async () => {
    setLoading(true);
    try {
      const res = await WorkspaceService.listWasteFindings({
        provider: providerFilter === 'ALL' ? undefined : providerFilter,
        severity: severityFilter === 'ALL' ? undefined : severityFilter,
        status: statusFilter === 'ALL' ? undefined : statusFilter,
        waste_type: wasteTypeFilter === 'ALL' ? undefined : wasteTypeFilter,
        limit: 100,
      });
      setFindings(res.items || []);
      if (selectedFinding) {
        const updated = (res.items || []).find((f: WasteFindingWorkspaceItem) => f.id === selectedFinding.id);
        if (updated) setSelectedFinding(updated);
      }
    } catch (err) {
      console.error('Failed to load waste findings', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFindings();
  }, [providerFilter, severityFilter, statusFilter, wasteTypeFilter]);

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const selectAll = () => {
    if (selectedIds.length === findings.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(findings.map((f) => f.id));
    }
  };

  const handleBatchSubmit = async (data: {
    reason?: string;
    snoozeDays?: number;
    assignedTo?: string;
  }) => {
    if (!batchAction) return;
    try {
      await WorkspaceService.batchWasteAction({
        finding_ids: selectedIds,
        action: batchAction,
        actor: 'finops.lead@enterprise.com',
        reason: data.reason,
        snooze_days: data.snoozeDays,
        assigned_to: data.assignedTo,
      });
      setSelectedIds([]);
      setBatchAction(null);
      await loadFindings();
    } catch (err) {
      console.error('Batch waste triage failed', err);
    }
  };

  const handleSingleAction = async (
    findingId: string,
    action: string,
    reason?: string,
    snoozeDays?: number,
    assignedTo?: string
  ) => {
    try {
      await WorkspaceService.performWasteAction(findingId, {
        action,
        actor: 'finops.lead@enterprise.com',
        reason,
        snooze_days: snoozeDays,
        assigned_to: assignedTo,
      });
      await loadFindings();
    } catch (err) {
      console.error('Single waste action failed', err);
    }
  };

  const totalCount = findings.length;
  const activeCount = findings.filter((f) => ['ACTIVE', 'OPEN', 'ACKNOWLEDGED'].includes(f.status)).length;
  const totalWaste = findings
    .filter((f) => ['ACTIVE', 'OPEN', 'ACKNOWLEDGED'].includes(f.status))
    .reduce((sum, f) => sum + Number(f.estimated_monthly_savings), 0);

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-100 tracking-tight">
            Enterprise Cloud Waste Management Workspace
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Continuous evidence-based detection of unattached disks, idle compute, orphaned snapshots, and unused IPs.
          </p>
        </div>

        <button
          onClick={() => loadFindings()}
          className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg border border-slate-700 transition"
        >
          Refresh
        </button>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="bg-slate-900 p-4 rounded-xl border border-slate-800">
          <div className="text-[11px] font-semibold uppercase text-slate-400">Total Findings</div>
          <div className="text-2xl font-bold text-slate-100 font-mono mt-1">{totalCount}</div>
        </div>

        <div className="bg-slate-900 p-4 rounded-xl border border-amber-500/30 bg-amber-950/20">
          <div className="text-[11px] font-semibold uppercase text-amber-400">Active / Open Findings</div>
          <div className="text-2xl font-bold text-amber-400 font-mono mt-1">{activeCount}</div>
        </div>

        <div className="bg-slate-900 p-4 rounded-xl border border-rose-500/30 bg-rose-950/20">
          <div className="text-[11px] font-semibold uppercase text-rose-400">Monthly Avoidable Waste</div>
          <div className="text-2xl font-bold text-rose-400 font-mono mt-1">${totalWaste.toFixed(2)}</div>
        </div>

        <div className="bg-slate-900 p-4 rounded-xl border border-rose-500/30 bg-rose-950/20">
          <div className="text-[11px] font-semibold uppercase text-rose-400">Annualized Waste</div>
          <div className="text-2xl font-bold text-rose-400 font-mono mt-1">${(totalWaste * 12).toFixed(2)}</div>
        </div>
      </div>

      {/* Filters Toolbar */}
      <div className="bg-slate-900 p-4 rounded-xl border border-slate-800 flex flex-wrap items-center justify-between gap-3">
        <div className="text-xs font-semibold text-slate-300">Filters:</div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Provider */}
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

          {/* Severity */}
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
          >
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>

          {/* Status */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
          >
            <option value="ALL">All Statuses</option>
            <option value="ACTIVE">Active</option>
            <option value="ACKNOWLEDGED">Acknowledged</option>
            <option value="SNOOZED">Snoozed</option>
            <option value="RESOLVED">Resolved</option>
            <option value="DISMISSED">Dismissed</option>
          </select>
        </div>
      </div>

      {/* Findings Table */}
      <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden shadow-sm">
        {loading ? (
          <div className="p-12 flex items-center justify-center text-slate-400 text-xs">
            <div className="w-5 h-5 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mr-3"></div>
            Loading waste workspace...
          </div>
        ) : findings.length === 0 ? (
          <div className="p-12 text-center text-slate-500 text-xs">
            No waste findings match your active filters.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/80 text-slate-400 uppercase text-[10px] font-mono border-b border-slate-800">
                <tr>
                  <th className="p-3 w-8">
                    <input
                      type="checkbox"
                      checked={selectedIds.length === findings.length && findings.length > 0}
                      onChange={selectAll}
                      className="rounded bg-slate-800 border-slate-700 text-indigo-600 focus:ring-0"
                    />
                  </th>
                  <th className="p-3">Resource & Finding</th>
                  <th className="p-3">Category</th>
                  <th className="p-3">Severity</th>
                  <th className="p-3">Status</th>
                  <th className="p-3 text-right">Monthly Waste</th>
                  <th className="p-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {findings.map((f) => {
                  const isSelected = selectedIds.includes(f.id);

                  return (
                    <tr
                      key={f.id}
                      className={`hover:bg-slate-800/40 transition ${isSelected ? 'bg-indigo-950/20' : ''}`}
                    >
                      <td className="p-3">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleSelect(f.id)}
                          className="rounded bg-slate-800 border-slate-700 text-indigo-600 focus:ring-0"
                        />
                      </td>

                      <td className="p-3 max-w-sm">
                        <div
                          onClick={() => setSelectedFinding(f)}
                          className="font-semibold text-slate-200 hover:text-indigo-400 cursor-pointer truncate"
                        >
                          {f.finding_title || f.waste_type}
                        </div>
                        <div className="text-[11px] text-slate-500 truncate mt-0.5 font-mono">
                          {f.resource_id}
                        </div>
                        {f.assigned_to && (
                          <span className="inline-block mt-1 text-[10px] font-mono bg-slate-800 px-1.5 py-0.5 rounded text-slate-400">
                            👤 {f.assigned_to}
                          </span>
                        )}
                      </td>

                      <td className="p-3">
                        <span className="text-[11px] font-mono text-slate-300 bg-slate-800/80 px-2 py-0.5 rounded">
                          {f.waste_type}
                        </span>
                      </td>

                      <td className="p-3">
                        <span
                          className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                            f.severity === 'CRITICAL'
                              ? 'bg-rose-500/20 text-rose-400'
                              : f.severity === 'HIGH'
                              ? 'bg-amber-500/20 text-amber-400'
                              : 'bg-blue-500/20 text-blue-400'
                          }`}
                        >
                          {f.severity}
                        </span>
                      </td>

                      <td className="p-3">
                        <span
                          className={`text-[10px] font-semibold px-2 py-0.5 rounded ${
                            f.status === 'RESOLVED'
                              ? 'bg-emerald-500/20 text-emerald-400'
                              : f.status === 'ACKNOWLEDGED'
                              ? 'bg-blue-500/20 text-blue-400'
                              : f.status === 'SNOOZED'
                              ? 'bg-purple-500/20 text-purple-400'
                              : f.status === 'DISMISSED'
                              ? 'bg-rose-500/20 text-rose-400'
                              : 'bg-amber-500/20 text-amber-400'
                          }`}
                        >
                          {f.status}
                        </span>
                      </td>

                      <td className="p-3 text-right font-mono font-bold text-rose-400">
                        ${Number(f.estimated_monthly_savings).toFixed(2)}
                      </td>

                      <td className="p-3 text-right">
                        <div className="flex items-center justify-end space-x-1.5">
                          <button
                            onClick={() => setSelectedFinding(f)}
                            className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs rounded transition"
                          >
                            Investigate
                          </button>
                          <button
                            onClick={() => handleSingleAction(f.id, 'ACKNOWLEDGE')}
                            className="px-2 py-1 bg-blue-600/20 hover:bg-blue-600/40 text-blue-300 text-xs rounded transition"
                            title="Acknowledge Finding"
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

      {/* Investigation Drawer */}
      {selectedFinding && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-xs">
          <div className="bg-slate-900 border-l border-slate-800 w-full max-w-2xl h-full flex flex-col shadow-2xl animate-in slide-in-from-right duration-200">
            {/* Header */}
            <div className="p-5 border-b border-slate-800 flex items-start justify-between">
              <div>
                <div className="flex items-center space-x-2">
                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-400 font-mono">
                    {selectedFinding.provider}
                  </span>
                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">
                    {selectedFinding.waste_type}
                  </span>
                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-400 font-mono">
                    ${Number(selectedFinding.estimated_monthly_savings).toFixed(2)}/mo
                  </span>
                </div>
                <h3 className="text-base font-bold text-slate-100 mt-1">
                  {selectedFinding.finding_title || selectedFinding.waste_type}
                </h3>
                <p className="text-xs text-slate-400 font-mono mt-0.5">{selectedFinding.resource_id}</p>
              </div>

              <button
                onClick={() => setSelectedFinding(null)}
                className="text-slate-400 hover:text-slate-200 p-1"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-slate-800 px-5 bg-slate-950/60 text-xs">
              {[
                { id: 'overview', label: 'Overview & Triage' },
                { id: 'telemetry', label: 'Telemetry Proof' },
                { id: 'playbook', label: 'Remediation Playbook' },
                { id: 'correlations', label: 'Correlated Impact' },
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

            {/* Contents */}
            <div className="flex-1 overflow-y-auto p-5 space-y-4">
              {activeTab === 'overview' && (
                <div className="space-y-4">
                  <div>
                    <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Detector Explanation</h4>
                    <p className="text-xs text-slate-300 mt-1 leading-relaxed bg-slate-950 p-3 rounded-lg border border-slate-800">
                      {selectedFinding.explanation || 'No detector explanation recorded.'}
                    </p>
                  </div>

                  <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-3">
                    <h4 className="text-xs font-semibold text-slate-300">Triage Lifecycle Controls</h4>
                    <div className="flex flex-wrap gap-2">
                      <button
                        onClick={() => handleSingleAction(selectedFinding.id, 'ACKNOWLEDGE')}
                        className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium rounded-lg transition"
                      >
                        Acknowledge
                      </button>
                      <button
                        onClick={() => {
                          const r = prompt('Reason for resolution:');
                          if (r) handleSingleAction(selectedFinding.id, 'RESOLVE', r);
                        }}
                        className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium rounded-lg transition"
                      >
                        Resolve
                      </button>
                      <button
                        onClick={() => handleSingleAction(selectedFinding.id, 'SNOOZE', undefined, 14)}
                        className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg transition"
                      >
                        Snooze (14d)
                      </button>
                      <button
                        onClick={() => {
                          const r = prompt('Reason for dismissal:');
                          if (r) handleSingleAction(selectedFinding.id, 'DISMISS', r);
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
                <TelemetryPanel wasteFindingId={selectedFinding.id} resourceId={selectedFinding.resource_id} />
              )}

              {activeTab === 'playbook' && (
                <RemediationPlaybookPanel wasteFindingId={selectedFinding.id} />
              )}

              {activeTab === 'correlations' && (
                <RelatedEvidencePanel wasteFindingId={selectedFinding.id} resourceId={selectedFinding.resource_id} />
              )}
            </div>
          </div>
        </div>
      )}

      {/* Batch Review Toolbar */}
      <BatchReviewToolbar
        selectedCount={selectedIds.length}
        onClearSelection={() => setSelectedIds([])}
        onAction={(act) => setBatchAction(act)}
        isWasteMode={true}
      />

      {/* Decision Modal */}
      <ReviewDecisionModal
        isOpen={batchAction !== null}
        action={batchAction || 'ACKNOWLEDGE'}
        itemCount={selectedIds.length}
        onClose={() => setBatchAction(null)}
        onSubmit={handleBatchSubmit}
      />
    </div>
  );
};
