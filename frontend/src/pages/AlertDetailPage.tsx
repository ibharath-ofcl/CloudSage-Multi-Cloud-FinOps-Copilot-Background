import React, { useEffect, useState } from 'react';
import {
  ArrowLeft,
  ShieldAlert,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Send,
  User,
  Ticket,
  Calendar,
  Layers,
  FileText,
  RefreshCw,
} from 'lucide-react';
import { useParams, useNavigate } from 'react-router-dom';
import { AlertService } from '../services/api';
import { AlertInstanceDetail, AlertHistory, NotificationOutbox } from '../types/alerts';

export const AlertDetailPage: React.FC = () => {
  const { alertId } = useParams<{ alertId: string }>();
  const [alert, setAlert] = useState<AlertInstanceDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [actionNotes, setActionNotes] = useState<string>('');
  const [ticketRef, setTicketRef] = useState<string>('');
  const [submittingAction, setSubmittingAction] = useState<boolean>(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const navigate = useNavigate();

  const fetchAlert = async () => {
    if (!alertId) return;
    setLoading(true);
    try {
      const res = await AlertService.getAlert(alertId);
      setAlert(res);
      setTicketRef(res.ticket_ref || '');
    } catch (err) {
      console.error('Failed to load alert detail', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlert();
  }, [alertId]);

  const handleAction = async (action: 'ACKNOWLEDGE' | 'INVESTIGATE' | 'RESOLVE' | 'SUPPRESS' | 'REOPEN') => {
    if (!alertId) return;
    if (action === 'RESOLVE' && !actionNotes.trim()) {
      setActionError('Resolution notes are required to resolve an alert.');
      return;
    }

    setSubmittingAction(true);
    setActionError(null);
    try {
      await AlertService.executeAction(alertId, {
        action,
        notes: actionNotes || undefined,
        suppress_hours: action === 'SUPPRESS' ? 24 : undefined,
        ticket_ref: ticketRef || undefined,
      });
      setActionNotes('');
      await fetchAlert();
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

  if (loading) {
    return (
      <div className="p-12 text-center text-slate-400 flex flex-col items-center justify-center min-h-[50vh]">
        <div className="w-8 h-8 border-4 border-rose-600 border-t-transparent rounded-full animate-spin mb-3" />
        <span className="text-xs">Loading alert instance...</span>
      </div>
    );
  }

  if (!alert) {
    return (
      <div className="p-12 text-center text-slate-500">
        <p className="text-sm font-semibold">Alert instance not found.</p>
        <button
          onClick={() => navigate('/alerts')}
          className="mt-3 text-xs text-blue-600 hover:underline cursor-pointer"
        >
          Return to Alerts Hub
        </button>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto text-xs">
      {/* Header */}
      <div>
        <button
          onClick={() => navigate('/alerts')}
          className="inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 font-semibold mb-2 cursor-pointer"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to Alerts Hub
        </button>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span
                className={`inline-block px-2 py-0.5 text-[10px] font-bold uppercase rounded border ${getSeverityBadgeClass(
                  alert.severity
                )}`}
              >
                {alert.severity}
              </span>
              <span
                className={`inline-block px-2 py-0.5 text-[10px] font-semibold rounded-full border ${getStatusBadgeClass(
                  alert.status
                )}`}
              >
                {alert.status}
              </span>
              {alert.escalation_level > 0 && (
                <span className="px-1.5 py-0.5 text-[9px] font-bold bg-rose-100 text-rose-800 rounded border border-rose-300">
                  Escalation Level {alert.escalation_level}
                </span>
              )}
            </div>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">{alert.title}</h1>
            <p className="text-slate-400 font-mono text-[11px]">DEDUP_KEY: {alert.dedup_key}</p>
          </div>

          <button
            onClick={fetchAlert}
            className="p-2 text-slate-500 hover:text-slate-800 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition shadow-xs cursor-pointer self-start sm:self-auto"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Financial Impact Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-[10px] font-semibold uppercase text-slate-500">Observed Spend</span>
          <div className="text-lg font-bold text-slate-900 font-mono mt-1">
            ${Number(alert.current_cost).toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-[10px] font-semibold uppercase text-slate-500">Expected Baseline</span>
          <div className="text-lg font-bold text-slate-600 font-mono mt-1">
            ${Number(alert.expected_cost).toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-rose-200 bg-rose-50/20 shadow-xs">
          <span className="text-[10px] font-semibold uppercase text-rose-700">Excess Cost Impact</span>
          <div className="text-lg font-bold text-rose-700 font-mono mt-1">
            ${Number(alert.excess_cost).toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-amber-200 bg-amber-50/20 shadow-xs">
          <span className="text-[10px] font-semibold uppercase text-amber-700">Spike Deviation</span>
          <div className="text-lg font-bold text-amber-700 font-mono mt-1">
            +{Number(alert.percentage_deviation).toFixed(1)}%
          </div>
        </div>
      </div>

      {/* Grid: Details & Triage Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Metadata & Cloud Scope */}
        <div className="lg:col-span-2 space-y-6">
          {/* Cloud Scope */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-5 space-y-4">
            <h2 className="font-bold text-slate-900 text-sm flex items-center gap-1.5">
              <Layers className="w-4 h-4 text-blue-600" />
              Cloud Scope & Attribution
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
              <div>
                <span className="text-slate-400 text-[11px]">Provider:</span>
                <p className="font-semibold text-slate-800">{alert.provider}</p>
              </div>
              <div>
                <span className="text-slate-400 text-[11px]">Service:</span>
                <p className="font-semibold text-slate-800">{alert.service_name}</p>
              </div>
              <div>
                <span className="text-slate-400 text-[11px]">Region:</span>
                <p className="font-semibold text-slate-800">{alert.region}</p>
              </div>
              <div>
                <span className="text-slate-400 text-[11px]">Account ID:</span>
                <p className="font-mono text-slate-800">{alert.account_id}</p>
              </div>
              <div>
                <span className="text-slate-400 text-[11px]">Target Resource:</span>
                <p className="font-mono text-slate-800 truncate" title={alert.resource_id || 'Service-Level Scope'}>
                  {alert.resource_id || 'Service-Level Scope'}
                </p>
              </div>
              <div>
                <span className="text-slate-400 text-[11px]">Trigger Count:</span>
                <p className="font-semibold text-slate-800">{alert.trigger_count} times</p>
              </div>
            </div>
          </div>

          {/* Linked Anomaly Root Cause Analysis */}
          {alert.anomaly && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-5 space-y-3">
              <h2 className="font-bold text-slate-900 text-sm flex items-center gap-1.5">
                <FileText className="w-4 h-4 text-purple-600" />
                Root Cause Analysis & Statistical Baseline
              </h2>
              <div className="space-y-2">
                <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-slate-700 leading-relaxed">
                  {typeof alert.anomaly.root_cause_analysis === 'string'
                    ? alert.anomaly.root_cause_analysis
                    : JSON.stringify(alert.anomaly.root_cause_analysis, null, 2)}
                </div>
                {alert.anomaly.z_score && (
                  <p className="text-[11px] text-slate-500 font-mono">
                    Statistical Z-Score: {Number(alert.anomaly.z_score).toFixed(2)} standard deviations above rolling baseline.
                  </p>
                )}
              </div>
            </div>
          )}

          {/* State Transition History Timeline */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-5 space-y-4">
            <h2 className="font-bold text-slate-900 text-sm flex items-center gap-1.5">
              <Clock className="w-4 h-4 text-emerald-600" />
              Alert Lifecycle Audit Trail
            </h2>

            {alert.history.length === 0 ? (
              <p className="text-slate-400 italic">No lifecycle transitions recorded yet.</p>
            ) : (
              <div className="relative pl-4 border-l-2 border-slate-200 space-y-4">
                {alert.history.map((h) => (
                  <div key={h.id} className="relative">
                    <div className="absolute -left-[21px] top-1 w-2.5 h-2.5 rounded-full bg-blue-600 border-2 border-white" />
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-slate-800">
                        {h.action} ({h.previous_status || 'INITIAL'} → {h.new_status})
                      </span>
                      <span className="text-[10px] text-slate-400">
                        {new Date(h.created_at).toLocaleString()}
                      </span>
                    </div>
                    <p className="text-slate-500 text-[11px] mt-0.5">Actor: {h.actor}</p>
                    {h.notes && (
                      <p className="text-slate-700 mt-1 bg-slate-50 p-2 rounded border border-slate-200 text-[11px]">
                        {h.notes}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right: Operational Triage & Delivery Attempts */}
        <div className="space-y-6">
          {/* Triage Action Form */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-5 space-y-4">
            <h2 className="font-bold text-slate-900 text-sm flex items-center gap-1.5">
              <ShieldAlert className="w-4 h-4 text-rose-600" />
              Triage & Governance Action
            </h2>

            {actionError && (
              <div className="p-2.5 bg-red-50 border border-red-200 rounded-lg text-red-700 text-xs">
                {actionError}
              </div>
            )}

            <div>
              <label className="block font-semibold text-slate-700 mb-1">Investigation Notes</label>
              <textarea
                rows={3}
                placeholder="Document findings or resolution rationale..."
                value={actionNotes}
                onChange={(e) => setActionNotes(e.target.value)}
                className="w-full p-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">Ticket Reference</label>
              <input
                type="text"
                placeholder="e.g. JIRA-1092"
                value={ticketRef}
                onChange={(e) => setTicketRef(e.target.value)}
                className="w-full p-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none"
              />
            </div>

            <div className="grid grid-cols-2 gap-2 pt-2">
              <button
                type="button"
                disabled={submittingAction || alert.status === 'ACKNOWLEDGED'}
                onClick={() => handleAction('ACKNOWLEDGE')}
                className="p-2 font-semibold text-blue-700 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 transition cursor-pointer disabled:opacity-50"
              >
                Acknowledge
              </button>
              <button
                type="button"
                disabled={submittingAction || alert.status === 'INVESTIGATING'}
                onClick={() => handleAction('INVESTIGATE')}
                className="p-2 font-semibold text-purple-700 bg-purple-50 border border-purple-200 rounded-lg hover:bg-purple-100 transition cursor-pointer disabled:opacity-50"
              >
                Investigate
              </button>
              <button
                type="button"
                disabled={submittingAction || alert.status === 'RESOLVED'}
                onClick={() => handleAction('RESOLVE')}
                className="p-2 font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-lg hover:bg-emerald-100 transition cursor-pointer disabled:opacity-50"
              >
                Resolve
              </button>
              <button
                type="button"
                disabled={submittingAction}
                onClick={() => handleAction('SUPPRESS')}
                className="p-2 font-semibold text-slate-700 bg-slate-100 border border-slate-300 rounded-lg hover:bg-slate-200 transition cursor-pointer disabled:opacity-50"
              >
                Suppress (24h)
              </button>
            </div>
          </div>

          {/* Outbox Notifications Dispatched */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-5 space-y-3">
            <h2 className="font-bold text-slate-900 text-sm flex items-center gap-1.5">
              <Send className="w-4 h-4 text-indigo-600" />
              Dispatched Notifications ({alert.deliveries.length})
            </h2>

            {alert.deliveries.length === 0 ? (
              <p className="text-slate-400 italic">No external notifications queued.</p>
            ) : (
              <div className="space-y-2">
                {alert.deliveries.map((del) => (
                  <div key={del.id} className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-slate-800 uppercase text-[10px]">
                        {del.channel}
                      </span>
                      <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-slate-200 text-slate-700">
                        {del.status}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-600 truncate mt-0.5">{del.recipient}</p>
                    <div className="flex items-center justify-between text-[10px] text-slate-400 mt-1">
                      <span>Attempts: {del.attempts}/{del.max_attempts}</span>
                      {del.delivered_at && <span>Delivered: {new Date(del.delivered_at).toLocaleTimeString()}</span>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
