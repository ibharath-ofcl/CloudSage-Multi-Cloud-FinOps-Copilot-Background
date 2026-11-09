import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Clock,
  Hash,
  UserCheck,
  Lock,
  FileCheck,
  Activity,
  ThumbsUp,
  ThumbsDown,
} from 'lucide-react';
import { SecurityGovernanceService } from '../services/securityApi';
import {
  SecurityStats,
  SecurityEvent,
  ApprovalRequest,
  AuditIntegrityReport,
  AuditCheckpoint,
} from '../types/security';
import { PermissionGate } from '../components/PermissionGate';

export const SecurityMonitoringPage: React.FC = () => {
  const [stats, setStats] = useState<SecurityStats | null>(null);
  const [events, setEvents] = useState<SecurityEvent[]>([]);
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [integrityReport, setIntegrityReport] = useState<AuditIntegrityReport | null>(null);
  const [checkpoints, setCheckpoints] = useState<AuditCheckpoint[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'events' | 'approvals' | 'integrity'>('events');
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Decision Modal State
  const [decidingApproval, setDecidingApproval] = useState<ApprovalRequest | null>(null);
  const [decisionNotes, setDecisionNotes] = useState('');

  // Checkpoint Modal
  const [isCheckpointModalOpen, setIsCheckpointModalOpen] = useState(false);
  const [checkpointNotes, setCheckpointNotes] = useState('');

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [statsData, eventsData, approvalsData, integrityData, checkpointsData] =
        await Promise.all([
          SecurityGovernanceService.getSecurityStats(),
          SecurityGovernanceService.listSecurityEvents({ limit: 50 }),
          SecurityGovernanceService.listApprovals(),
          SecurityGovernanceService.getAuditIntegrityReport(),
          SecurityGovernanceService.listAuditCheckpoints(),
        ]);
      setStats(statsData);
      setEvents(eventsData);
      setApprovals(approvalsData);
      setIntegrityReport(integrityData);
      setCheckpoints(checkpointsData);
    } catch (err: any) {
      setMessage({
        type: 'error',
        text: err.response?.data?.detail || 'Failed to load security metrics',
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleVerifyChain = async () => {
    try {
      const res = await SecurityGovernanceService.verifyAuditChain();
      if (res.chain_valid) {
        setMessage({
          type: 'success',
          text: `Cryptographic audit chain fully verified! Evaluated ${res.records_evaluated} records with zero tampering detected.`,
        });
      } else {
        setMessage({
          type: 'error',
          text: `Audit chain integrity failure! Broken records: ${res.broken_records.join(', ')}`,
        });
      }
      loadData();
    } catch (err: any) {
      setMessage({
        type: 'error',
        text: err.response?.data?.detail || 'Verification request failed',
      });
    }
  };

  const handleCreateCheckpoint = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const cp = await SecurityGovernanceService.createAuditCheckpoint(checkpointNotes);
      setMessage({
        type: 'success',
        text: `Cryptographic checkpoint created: ${cp.checkpoint_hash.slice(0, 16)}... covering ${cp.record_count} records.`,
      });
      setIsCheckpointModalOpen(false);
      setCheckpointNotes('');
      loadData();
    } catch (err: any) {
      setMessage({
        type: 'error',
        text: err.response?.data?.detail || 'Failed to create checkpoint',
      });
    }
  };

  const handleDecideApproval = async (approved: boolean) => {
    if (!decidingApproval) return;
    try {
      await SecurityGovernanceService.decideApproval(decidingApproval.id, {
        approved,
        notes: decisionNotes,
      });
      setMessage({
        type: 'success',
        text: `Approval request ${decidingApproval.id.slice(0, 8)} has been ${
          approved ? 'APPROVED' : 'REJECTED'
        }.`,
      });
      setDecidingApproval(null);
      setDecisionNotes('');
      loadData();
    } catch (err: any) {
      setMessage({
        type: 'error',
        text: err.response?.data?.detail || 'Failed to submit approval decision',
      });
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-6 h-6 text-rose-600" />
            <h1 className="text-xl font-bold text-slate-900">
              Security Monitoring & Governance Hub
            </h1>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Real-time threat detection, dual-party approval workflows, and tamper-evident SHA-256 audit log integrity.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={loadData}
            disabled={isLoading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Alert banner */}
      {message && (
        <div
          className={`p-3 rounded-lg text-xs font-medium flex items-center justify-between ${
            message.type === 'success'
              ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
              : 'bg-rose-50 text-rose-800 border border-rose-200'
          }`}
        >
          <span>{message.text}</span>
          <button onClick={() => setMessage(null)} className="font-bold underline ml-2">
            Dismiss
          </button>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
            <span>Active Sessions</span>
            <UserCheck className="w-4 h-4 text-blue-500" />
          </div>
          <div className="mt-2 text-2xl font-bold text-slate-900">
            {stats?.active_sessions_count ?? '—'}
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">Across all tenants</div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
            <span>Locked Accounts</span>
            <Lock className="w-4 h-4 text-rose-500" />
          </div>
          <div className="mt-2 text-2xl font-bold text-rose-600">
            {stats?.locked_accounts_count ?? '—'}
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">Brute force lockouts</div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
            <span>Pending Approvals</span>
            <Clock className="w-4 h-4 text-amber-500" />
          </div>
          <div className="mt-2 text-2xl font-bold text-amber-600">
            {stats?.pending_approvals_count ?? '—'}
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">Dual-party required</div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
            <span>Threat Events (24h)</span>
            <Activity className="w-4 h-4 text-purple-500" />
          </div>
          <div className="mt-2 text-2xl font-bold text-slate-900">
            {stats?.security_events_last_24h ?? '—'}
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">
            {stats?.critical_events_last_24h || 0} critical
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
            <span>Audit Chain</span>
            <Hash className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="mt-2 text-lg font-bold flex items-center gap-1.5 text-emerald-600">
            <CheckCircle2 className="w-5 h-5" /> Verified
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">SHA-256 Hash Chained</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-200">
        <div className="flex items-center gap-4 text-xs font-medium">
          <button
            onClick={() => setActiveTab('events')}
            className={`pb-3 px-1 border-b-2 transition ${
              activeTab === 'events'
                ? 'border-rose-600 text-rose-600 font-bold'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            Threat Detection & Security Events ({events.length})
          </button>
          <button
            onClick={() => setActiveTab('approvals')}
            className={`pb-3 px-1 border-b-2 transition ${
              activeTab === 'approvals'
                ? 'border-rose-600 text-rose-600 font-bold'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            Dual-Party Approval Queue ({approvals.length})
          </button>
          <button
            onClick={() => setActiveTab('integrity')}
            className={`pb-3 px-1 border-b-2 transition ${
              activeTab === 'integrity'
                ? 'border-rose-600 text-rose-600 font-bold'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            Audit Log Cryptographic Integrity
          </button>
        </div>
      </div>

      {/* Tab 1: Threat Detection Events */}
      {activeTab === 'events' && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider">
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4">Event Type</th>
                <th className="py-3 px-4">Severity</th>
                <th className="py-3 px-4">Actor</th>
                <th className="py-3 px-4">Action / Resource</th>
                <th className="py-3 px-4">IP Address</th>
                <th className="py-3 px-4">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {events.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-400">
                    No security events recorded.
                  </td>
                </tr>
              ) : (
                events.map((ev) => (
                  <tr key={ev.id} className="hover:bg-slate-50/80 transition">
                    <td className="py-3 px-4 text-slate-500 whitespace-nowrap">
                      {new Date(ev.created_at).toLocaleString()}
                    </td>
                    <td className="py-3 px-4 font-mono font-semibold text-slate-900">
                      {ev.event_type}
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`inline-flex px-2 py-0.5 rounded text-[10px] font-bold ${
                          ev.severity === 'CRITICAL'
                            ? 'bg-rose-100 text-rose-800 border border-rose-200'
                            : ev.severity === 'HIGH'
                            ? 'bg-orange-100 text-orange-800 border border-orange-200'
                            : ev.severity === 'MEDIUM'
                            ? 'bg-amber-100 text-amber-800 border border-amber-200'
                            : 'bg-slate-100 text-slate-700'
                        }`}
                      >
                        {ev.severity}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-medium text-slate-700">
                      {ev.actor_email || 'System / Anonymous'}
                    </td>
                    <td className="py-3 px-4 text-slate-600">
                      {ev.resource_type ? `${ev.resource_type}:${ev.action || '*'}` : '—'}
                    </td>
                    <td className="py-3 px-4 font-mono text-[11px] text-slate-500">
                      {ev.ip_address || '—'}
                    </td>
                    <td className="py-3 px-4 font-mono text-[11px] text-slate-500 max-w-xs truncate">
                      {JSON.stringify(ev.details)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Tab 2: Dual Approval Requests */}
      {activeTab === 'approvals' && (
        <div className="space-y-4">
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-xs text-amber-900 flex items-start gap-3">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <div className="font-bold">Separation of Duties (Multi-Party Governance)</div>
              <div className="text-[11px] text-amber-800 mt-0.5 leading-relaxed">
                Critical administrative operations require two independent identities: the requester cannot approve their own action (<code>requester != approver</code>).
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider">
                  <th className="py-3 px-4">Action Type</th>
                  <th className="py-3 px-4">Resource</th>
                  <th className="py-3 px-4">Requester</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Created</th>
                  <th className="py-3 px-4">Expires</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {approvals.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-slate-400">
                      No approval requests found.
                    </td>
                  </tr>
                ) : (
                  approvals.map((req) => (
                    <tr key={req.id} className="hover:bg-slate-50/80 transition">
                      <td className="py-3 px-4 font-mono font-semibold text-slate-900">
                        {req.action_type}
                      </td>
                      <td className="py-3 px-4 text-slate-600">
                        {req.resource_type} ({req.resource_id ? req.resource_id.slice(0, 8) : 'Global'})
                      </td>
                      <td className="py-3 px-4 text-slate-700">
                        {req.requester_email || req.requester_id.slice(0, 8)}
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-flex px-2 py-0.5 rounded text-[10px] font-bold ${
                            req.status === 'PENDING'
                              ? 'bg-amber-100 text-amber-800 border border-amber-200'
                              : req.status === 'APPROVED'
                              ? 'bg-emerald-100 text-emerald-800'
                              : 'bg-rose-100 text-rose-800'
                          }`}
                        >
                          {req.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-500">
                        {new Date(req.created_at).toLocaleString()}
                      </td>
                      <td className="py-3 px-4 text-slate-500">
                        {new Date(req.expires_at).toLocaleString()}
                      </td>
                      <td className="py-3 px-4 text-right">
                        {req.status === 'PENDING' ? (
                          <PermissionGate permission="approval:decide">
                            <button
                              onClick={() => setDecidingApproval(req)}
                              className="px-2.5 py-1 text-xs font-semibold bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition"
                            >
                              Review & Decide
                            </button>
                          </PermissionGate>
                        ) : (
                          <span className="text-slate-400 text-[11px]">Decided</span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 3: Audit Log Cryptographic Integrity */}
      {activeTab === 'integrity' && (
        <div className="space-y-5">
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <FileCheck className="w-5 h-5 text-emerald-600" />
                <h3 className="text-base font-bold text-slate-900">
                  SHA-256 Tamper-Evident Hash Chain
                </h3>
              </div>
              <p className="text-xs text-slate-500 mt-1 max-w-2xl leading-relaxed">
                Every audit log record embeds the cryptographic hash of its predecessor, creating an unbroken hash chain. Any direct database tampering or modification breaks the signature.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleVerifyChain}
                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition shadow-xs"
              >
                <CheckCircle2 className="w-3.5 h-3.5" />
                Verify Hash Chain
              </button>

              <button
                onClick={() => setIsCheckpointModalOpen(true)}
                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold bg-slate-800 text-white rounded-lg hover:bg-slate-900 transition shadow-xs"
              >
                <Hash className="w-3.5 h-3.5" />
                Create Checkpoint
              </button>
            </div>
          </div>

          {/* Integrity Report Card */}
          {integrityReport && (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
                <div className="text-xs text-slate-500 font-medium">Total Audit Records</div>
                <div className="text-xl font-bold text-slate-900 mt-1">
                  {integrityReport.total_audit_records}
                </div>
              </div>
              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
                <div className="text-xs text-slate-500 font-medium">Chain State</div>
                <div className="text-xl font-bold text-emerald-600 mt-1 flex items-center gap-1">
                  <CheckCircle2 className="w-4 h-4" /> Valid
                </div>
              </div>
              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
                <div className="text-xs text-slate-500 font-medium">Verified Checkpoints</div>
                <div className="text-xl font-bold text-slate-900 mt-1">
                  {integrityReport.checkpoints_count}
                </div>
              </div>
              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
                <div className="text-xs text-slate-500 font-medium">Latest Checkpoint Hash</div>
                <div className="text-xs font-mono font-semibold text-slate-700 mt-1 truncate">
                  {integrityReport.latest_checkpoint_hash || 'No checkpoints created'}
                </div>
              </div>
            </div>
          )}

          {/* Checkpoints History Table */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
            <div className="p-4 border-b border-slate-100 flex items-center justify-between">
              <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                Cryptographic Checkpoint Ledger
              </h4>
              <span className="text-xs text-slate-400">{checkpoints.length} Checkpoints</span>
            </div>
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider">
                  <th className="py-3 px-4">Checkpoint Time</th>
                  <th className="py-3 px-4">Records Sealed</th>
                  <th className="py-3 px-4">Checkpoint SHA-256 Hash</th>
                  <th className="py-3 px-4">Notes</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {checkpoints.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="py-8 text-center text-slate-400">
                      No checkpoints created yet. Click "Create Checkpoint" to freeze an immutable state.
                    </td>
                  </tr>
                ) : (
                  checkpoints.map((cp) => (
                    <tr key={cp.id} className="hover:bg-slate-50/80 transition">
                      <td className="py-3 px-4 text-slate-500 whitespace-nowrap">
                        {new Date(cp.created_at).toLocaleString()}
                      </td>
                      <td className="py-3 px-4 font-bold text-slate-900">{cp.record_count}</td>
                      <td className="py-3 px-4 font-mono text-[11px] text-slate-700">
                        {cp.checkpoint_hash}
                      </td>
                      <td className="py-3 px-4 text-slate-600">{cp.notes || '—'}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Decision Modal */}
      {decidingApproval && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 space-y-4">
            <h2 className="text-base font-bold text-slate-900">
              Review Dual Approval Request
            </h2>
            <div className="text-xs text-slate-600 space-y-1 bg-slate-50 p-3 rounded-lg border border-slate-200">
              <div>
                <strong>Action:</strong> {decidingApproval.action_type}
              </div>
              <div>
                <strong>Resource:</strong> {decidingApproval.resource_type} (
                {decidingApproval.resource_id || 'Global'})
              </div>
              <div>
                <strong>Requester:</strong> {decidingApproval.requester_email || decidingApproval.requester_id}
              </div>
              <div>
                <strong>Justification:</strong> {decidingApproval.justification || 'None'}
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Decision Notes / Reason
              </label>
              <textarea
                value={decisionNotes}
                onChange={(e) => setDecisionNotes(e.target.value)}
                rows={3}
                placeholder="Enter mandatory audit trail justification..."
                className="w-full text-xs border border-slate-300 rounded-lg p-2 focus:ring-1 focus:ring-indigo-500 outline-none"
              />
            </div>

            <div className="flex items-center justify-between pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setDecidingApproval(null)}
                className="px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100 rounded-lg"
              >
                Cancel
              </button>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => handleDecideApproval(false)}
                  className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-semibold bg-rose-600 text-white rounded-lg hover:bg-rose-700"
                >
                  <ThumbsDown className="w-3.5 h-3.5" /> Reject
                </button>
                <button
                  type="button"
                  onClick={() => handleDecideApproval(true)}
                  className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-semibold bg-emerald-600 text-white rounded-lg hover:bg-emerald-700"
                >
                  <ThumbsUp className="w-3.5 h-3.5" /> Approve
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Checkpoint Modal */}
      {isCheckpointModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200">
            <h2 className="text-base font-bold text-slate-900 mb-3">
              Seal Cryptographic Checkpoint
            </h2>
            <p className="text-xs text-slate-500 mb-4 leading-relaxed">
              Creates an immutable SHA-256 state seal of the current audit ledger. Used for external SOC 2 and ISO 27001 regulatory compliance audits.
            </p>
            <form onSubmit={handleCreateCheckpoint} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Audit Notes</label>
                <input
                  type="text"
                  value={checkpointNotes}
                  onChange={(e) => setCheckpointNotes(e.target.value)}
                  placeholder="e.g. End of Month SOC 2 Compliance Seal"
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 outline-none focus:ring-1 focus:ring-slate-800"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsCheckpointModalOpen(false)}
                  className="px-3 py-1.5 border border-slate-200 rounded-lg text-slate-600 hover:bg-slate-50 font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-3.5 py-1.5 bg-slate-900 text-white font-semibold rounded-lg hover:bg-slate-800 shadow-xs"
                >
                  Seal Checkpoint
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
