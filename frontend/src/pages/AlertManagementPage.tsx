import React, { useEffect, useState } from 'react';
import {
  AlertTriangle,
  ShieldAlert,
  Clock,
  CheckCircle2,
  Eye,
  Filter,
  Search,
  Sliders,
  Send,
  ExternalLink,
  RefreshCw,
  X,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { AlertService } from '../services/api';
import { AlertInstance, AlertStats, AlertSeverity, AlertLifecycleStatus } from '../types/alerts';

export const AlertManagementPage: React.FC = () => {
  const [alerts, setAlerts] = useState<AlertInstance[]>([]);
  const [stats, setStats] = useState<AlertStats | null>(null);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const navigate = useNavigate();

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [severityFilter, setSeverityFilter] = useState<string>('');
  const [providerFilter, setProviderFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Lifecycle Action Modal
  const [selectedAlert, setSelectedAlert] = useState<AlertInstance | null>(null);
  const [actionType, setActionType] = useState<'ACKNOWLEDGE' | 'INVESTIGATE' | 'RESOLVE' | 'SUPPRESS' | 'REOPEN'>('ACKNOWLEDGE');
  const [actionNotes, setActionNotes] = useState<string>('');
  const [suppressHours, setSuppressHours] = useState<number>(24);
  const [ticketRef, setTicketRef] = useState<string>('');
  const [submittingAction, setSubmittingAction] = useState<boolean>(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const fetchAlertsAndStats = async () => {
    setLoading(true);
    try {
      const [statsRes, alertsRes] = await Promise.all([
        AlertService.getStats(),
        AlertService.listAlerts({
          status: statusFilter || undefined,
          severity: severityFilter || undefined,
          provider: providerFilter || undefined,
          search: searchQuery || undefined,
          limit: 100,
        }),
      ]);
      setStats(statsRes);
      setAlerts(alertsRes.items || []);
      setTotalCount(alertsRes.total || 0);
    } catch (err) {
      console.error('Failed to load alerts or statistics', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlertsAndStats();
  }, [statusFilter, severityFilter, providerFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchAlertsAndStats();
  };

  const handleOpenActionModal = (alert: AlertInstance, defaultAction: 'ACKNOWLEDGE' | 'INVESTIGATE' | 'RESOLVE' | 'SUPPRESS' | 'REOPEN') => {
    setSelectedAlert(alert);
    setActionType(defaultAction);
    setActionNotes('');
    setSuppressHours(24);
    setTicketRef('');
    setActionError(null);
  };

  const handleSubmitAction = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAlert) return;

    if (actionType === 'RESOLVE' && !actionNotes.trim()) {
      setActionError('Resolution notes are required when marking an alert as resolved.');
      return;
    }
    if (actionType === 'SUPPRESS' && !actionNotes.trim()) {
      setActionError('Suppression rationale is required.');
      return;
    }

    setSubmittingAction(true);
    setActionError(null);
    try {
      const updated = await AlertService.executeAction(selectedAlert.id, {
        action: actionType,
        notes: actionNotes || undefined,
        suppress_hours: actionType === 'SUPPRESS' ? suppressHours : undefined,
        ticket_ref: ticketRef || undefined,
      });

      // Update in local state
      setAlerts((prev) => prev.map((a) => (a.id === updated.id ? updated : a)));
      setSelectedAlert(null);
      // Refresh stats
      AlertService.getStats().then(setStats);
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Failed to execute lifecycle action.');
    } finally {
      setSubmittingAction(false);
    }
  };

  const getSeverityBadgeClass = (severity: string) => {
    switch (severity?.toUpperCase()) {
      case 'CRITICAL':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'HIGH':
        return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'MEDIUM':
        return 'bg-amber-100 text-amber-800 border-amber-200';
      default:
        return 'bg-blue-100 text-blue-800 border-blue-200';
    }
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status?.toUpperCase()) {
      case 'OPEN':
        return 'bg-red-50 text-red-700 border-red-200';
      case 'ACKNOWLEDGED':
        return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'INVESTIGATING':
        return 'bg-purple-50 text-purple-700 border-purple-200';
      case 'RESOLVED':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'SUPPRESSED':
        return 'bg-slate-100 text-slate-600 border-slate-300';
      default:
        return 'bg-slate-50 text-slate-700 border-slate-200';
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-rose-600" />
            Cost Anomaly Alerts Hub
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Enterprise multi-cloud cost anomaly triage, alert lifecycle governance, and cooldown deduplication.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate('/alert-rules')}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition shadow-xs cursor-pointer"
          >
            <Sliders className="w-3.5 h-3.5 text-slate-500" />
            Configure Alert Rules
          </button>
          <button
            onClick={() => navigate('/notification-deliveries')}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-indigo-700 bg-indigo-50 border border-indigo-200 rounded-lg hover:bg-indigo-100 transition shadow-xs cursor-pointer"
          >
            <Send className="w-3.5 h-3.5" />
            Delivery Outbox
          </button>
          <button
            onClick={fetchAlertsAndStats}
            className="p-1.5 text-slate-500 hover:text-slate-800 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition shadow-xs cursor-pointer"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* KPI Stats Overview */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="text-[11px] font-semibold uppercase text-slate-500">Active Alerts</div>
          <div className="text-xl font-bold text-slate-900 font-mono mt-1">
            {stats?.active_alerts ?? '-'}
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-red-200 bg-red-50/20 shadow-xs">
          <div className="text-[11px] font-semibold uppercase text-red-700">Critical Alerts</div>
          <div className="text-xl font-bold text-red-700 font-mono mt-1">
            {stats?.critical_alerts ?? '-'}
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-orange-200 bg-orange-50/20 shadow-xs">
          <div className="text-[11px] font-semibold uppercase text-orange-700">High Alerts</div>
          <div className="text-xl font-bold text-orange-700 font-mono mt-1">
            {stats?.high_alerts ?? '-'}
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-purple-200 bg-purple-50/20 shadow-xs">
          <div className="text-[11px] font-semibold uppercase text-purple-700">Investigating</div>
          <div className="text-xl font-bold text-purple-700 font-mono mt-1">
            {stats?.investigating_alerts ?? '-'}
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-emerald-200 bg-emerald-50/20 shadow-xs">
          <div className="text-[11px] font-semibold uppercase text-emerald-700">Resolved</div>
          <div className="text-xl font-bold text-emerald-700 font-mono mt-1">
            {stats?.resolved_alerts ?? '-'}
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="text-[11px] font-semibold uppercase text-slate-500">24h Failures</div>
          <div className="text-xl font-bold text-slate-700 font-mono mt-1">
            {stats?.delivery_failures_24h ?? 0}
          </div>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-4 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex flex-wrap items-center gap-2">
          {/* Status Filter */}
          <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1">
            <span className="text-slate-500 font-medium">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-transparent font-semibold text-slate-800 focus:outline-none cursor-pointer"
            >
              <option value="">All Statuses</option>
              <option value="OPEN">Open (Unacknowledged)</option>
              <option value="ACKNOWLEDGED">Acknowledged</option>
              <option value="INVESTIGATING">Investigating</option>
              <option value="RESOLVED">Resolved</option>
              <option value="SUPPRESSED">Suppressed</option>
            </select>
          </div>

          {/* Severity Filter */}
          <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1">
            <span className="text-slate-500 font-medium">Severity:</span>
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="bg-transparent font-semibold text-slate-800 focus:outline-none cursor-pointer"
            >
              <option value="">All Severities</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
            </select>
          </div>

          {/* Provider Filter */}
          <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1">
            <span className="text-slate-500 font-medium">Cloud:</span>
            <select
              value={providerFilter}
              onChange={(e) => setProviderFilter(e.target.value)}
              className="bg-transparent font-semibold text-slate-800 focus:outline-none cursor-pointer"
            >
              <option value="">All Clouds</option>
              <option value="AWS">AWS</option>
              <option value="AZURE">Azure</option>
              <option value="GCP">GCP</option>
            </select>
          </div>
        </div>

        {/* Search */}
        <form onSubmit={handleSearchSubmit} className="relative w-full sm:w-64">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search service, account, title..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500 text-slate-800"
          />
        </form>
      </div>

      {/* Alerts Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-600">
            <thead className="bg-slate-50/80 border-b border-slate-200 text-slate-700 uppercase font-semibold text-[10px] tracking-wider">
              <tr>
                <th className="py-3 px-4">Severity / Title</th>
                <th className="py-3 px-4">Cloud Provider & Service</th>
                <th className="py-3 px-4">Account / Region</th>
                <th className="py-3 px-4">Excess Cost Impact</th>
                <th className="py-3 px-4">Deviation</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Last Triggered</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    <div className="w-6 h-6 border-2 border-rose-600 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                    Loading alert instances...
                  </td>
                </tr>
              ) : alerts.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    <ShieldAlert className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                    No alert instances match the selected criteria.
                  </td>
                </tr>
              ) : (
                alerts.map((alert) => (
                  <tr key={alert.id} className="hover:bg-slate-50/70 transition">
                    <td className="py-3.5 px-4 font-medium text-slate-900 max-w-xs">
                      <div className="flex items-center gap-2">
                        <span
                          className={`inline-block px-1.5 py-0.5 text-[9px] font-bold uppercase rounded border ${getSeverityBadgeClass(
                            alert.severity
                          )}`}
                        >
                          {alert.severity}
                        </span>
                        <span
                          onClick={() => navigate(`/alerts/${alert.id}`)}
                          className="truncate hover:text-blue-600 cursor-pointer font-semibold"
                          title={alert.title}
                        >
                          {alert.title}
                        </span>
                      </div>
                      {alert.escalation_level > 0 && (
                        <span className="inline-block mt-1 text-[10px] font-semibold text-rose-600 bg-rose-50 border border-rose-200 px-1.5 rounded">
                          Escalated (Level {alert.escalation_level})
                        </span>
                      )}
                    </td>

                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-slate-800">{alert.service_name}</div>
                      <div className="text-[11px] text-slate-400">{alert.provider}</div>
                    </td>

                    <td className="py-3.5 px-4">
                      <div className="font-mono text-slate-700">{alert.account_id}</div>
                      <div className="text-[11px] text-slate-400">{alert.region}</div>
                    </td>

                    <td className="py-3.5 px-4 font-mono font-bold text-rose-700">
                      ${Number(alert.excess_cost).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>

                    <td className="py-3.5 px-4 font-mono font-semibold text-slate-800">
                      +{Number(alert.percentage_deviation).toFixed(1)}%
                    </td>

                    <td className="py-3.5 px-4">
                      <span
                        className={`inline-block px-2 py-0.5 text-[10px] font-semibold rounded-full border ${getStatusBadgeClass(
                          alert.status
                        )}`}
                      >
                        {alert.status}
                      </span>
                      {alert.suppress_until && new Date(alert.suppress_until) > new Date() && (
                        <div className="text-[10px] text-slate-400 flex items-center gap-0.5 mt-0.5">
                          <Clock className="w-2.5 h-2.5" />
                          Suppressed
                        </div>
                      )}
                    </td>

                    <td className="py-3.5 px-4 text-slate-500 text-[11px]">
                      <div>{new Date(alert.last_triggered_at).toLocaleDateString()}</div>
                      <div className="text-[10px] text-slate-400">
                        {new Date(alert.last_triggered_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </div>
                    </td>

                    <td className="py-3.5 px-4 text-right space-x-1">
                      <button
                        onClick={() => navigate(`/alerts/${alert.id}`)}
                        className="p-1 text-slate-400 hover:text-slate-700 rounded transition cursor-pointer"
                        title="View Details"
                      >
                        <Eye className="w-4 h-4" />
                      </button>

                      {alert.status === 'OPEN' && (
                        <button
                          onClick={() => handleOpenActionModal(alert, 'ACKNOWLEDGE')}
                          className="px-2 py-1 text-[11px] font-semibold text-blue-700 bg-blue-50 border border-blue-200 rounded hover:bg-blue-100 transition cursor-pointer"
                        >
                          Ack
                        </button>
                      )}

                      {(alert.status === 'OPEN' || alert.status === 'ACKNOWLEDGED') && (
                        <button
                          onClick={() => handleOpenActionModal(alert, 'INVESTIGATE')}
                          className="px-2 py-1 text-[11px] font-semibold text-purple-700 bg-purple-50 border border-purple-200 rounded hover:bg-purple-100 transition cursor-pointer"
                        >
                          Investigate
                        </button>
                      )}

                      {alert.status !== 'RESOLVED' && (
                        <button
                          onClick={() => handleOpenActionModal(alert, 'RESOLVE')}
                          className="px-2 py-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 rounded hover:bg-emerald-100 transition cursor-pointer"
                        >
                          Resolve
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Lifecycle Action Modal */}
      {selectedAlert && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
          <div className="bg-white rounded-xl border border-slate-200 shadow-2xl w-full max-w-md overflow-hidden text-xs">
            <div className="px-5 py-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
              <div>
                <h3 className="font-bold text-slate-900 text-sm">Alert Lifecycle Action</h3>
                <p className="text-[11px] text-slate-500 truncate max-w-xs">{selectedAlert.title}</p>
              </div>
              <button
                onClick={() => setSelectedAlert(null)}
                className="text-slate-400 hover:text-slate-600 cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSubmitAction} className="p-5 space-y-4">
              {actionError && (
                <div className="p-2.5 bg-red-50 border border-red-200 rounded-lg text-red-700 text-xs">
                  {actionError}
                </div>
              )}

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Select Action</label>
                <select
                  value={actionType}
                  onChange={(e) => setActionType(e.target.value as any)}
                  className="w-full p-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500 font-semibold"
                >
                  <option value="ACKNOWLEDGE">Acknowledge (Stop Escalation)</option>
                  <option value="INVESTIGATE">Start Investigation</option>
                  <option value="RESOLVE">Resolve Alert (Require Notes)</option>
                  <option value="SUPPRESS">Suppress (Snooze Alert)</option>
                  <option value="REOPEN">Reopen Alert</option>
                </select>
              </div>

              {actionType === 'SUPPRESS' && (
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Suppression Duration (Hours)</label>
                  <input
                    type="number"
                    min="1"
                    max="720"
                    value={suppressHours}
                    onChange={(e) => setSuppressHours(Number(e.target.value))}
                    className="w-full p-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              )}

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  {actionType === 'RESOLVE' ? 'Resolution Notes *' : 'Investigation Notes / Rationale'}
                </label>
                <textarea
                  rows={3}
                  value={actionNotes}
                  onChange={(e) => setActionNotes(e.target.value)}
                  placeholder={
                    actionType === 'RESOLVE'
                      ? 'Describe root cause identified and remediation applied (e.g. idle compute stopped)...'
                      : 'Add notes for FinOps audit trail...'
                  }
                  className="w-full p-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Ticket Reference (Optional)</label>
                <input
                  type="text"
                  placeholder="e.g. JIRA-4092, INC-8291"
                  value={ticketRef}
                  onChange={(e) => setTicketRef(e.target.value)}
                  className="w-full p-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <div className="pt-2 flex items-center justify-end gap-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setSelectedAlert(null)}
                  className="px-3 py-1.5 text-xs text-slate-600 hover:text-slate-800 rounded-lg cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingAction}
                  className="px-4 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition shadow-xs disabled:opacity-50 cursor-pointer"
                >
                  {submittingAction ? 'Applying...' : 'Confirm Action'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
