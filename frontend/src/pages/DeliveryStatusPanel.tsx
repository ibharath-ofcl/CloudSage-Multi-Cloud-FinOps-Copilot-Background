import React, { useEffect, useState } from 'react';
import {
  Send,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Clock,
  RotateCcw,
  Ban,
  Activity,
  Mail,
  Webhook,
  Bell,
  ArrowLeft,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { NotificationService } from '../services/api';
import { NotificationOutbox, NotificationHealth } from '../types/alerts';

export const DeliveryStatusPanel: React.FC = () => {
  const [outboxItems, setOutboxItems] = useState<NotificationOutbox[]>([]);
  const [health, setHealth] = useState<NotificationHealth | null>(null);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [channelFilter, setChannelFilter] = useState<string>('');
  const [dispatching, setDispatching] = useState<boolean>(false);
  const navigate = useNavigate();

  const fetchOutboxAndHealth = async () => {
    setLoading(true);
    try {
      const [healthRes, outboxRes] = await Promise.all([
        NotificationService.getPipelineHealth(),
        NotificationService.listOutbox({
          status: statusFilter || undefined,
          channel: channelFilter || undefined,
          limit: 100,
        }),
      ]);
      setHealth(healthRes);
      setOutboxItems(outboxRes.items || []);
      setTotalCount(outboxRes.total || 0);
    } catch (err) {
      console.error('Failed to load delivery pipeline data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOutboxAndHealth();
  }, [statusFilter, channelFilter]);

  const handleRetry = async (outboxId: string) => {
    try {
      await NotificationService.retryOutbox(outboxId);
      await fetchOutboxAndHealth();
    } catch (err) {
      console.error('Failed to retry outbox item', err);
    }
  };

  const handleCancel = async (outboxId: string) => {
    try {
      await NotificationService.cancelOutbox(outboxId);
      await fetchOutboxAndHealth();
    } catch (err) {
      console.error('Failed to cancel outbox item', err);
    }
  };

  const handleTriggerDispatch = async () => {
    setDispatching(true);
    try {
      await NotificationService.dispatchOutbox(50);
      await fetchOutboxAndHealth();
    } catch (err) {
      console.error('Failed to dispatch outbox', err);
    } finally {
      setDispatching(false);
    }
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status?.toUpperCase()) {
      case 'DELIVERED':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'PENDING':
        return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'PROCESSING':
        return 'bg-purple-50 text-purple-700 border-purple-200';
      case 'RETRYING':
        return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'DEAD_LETTERED':
        return 'bg-rose-100 text-rose-800 border-rose-300';
      case 'FAILED':
        return 'bg-red-50 text-red-700 border-red-200';
      default:
        return 'bg-slate-100 text-slate-600 border-slate-200';
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto text-xs">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <button
            onClick={() => navigate('/alerts')}
            className="inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 font-semibold mb-1 cursor-pointer"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to Alerts Hub
          </button>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <Send className="w-5 h-5 text-indigo-600" />
            Notification Outbox & Delivery Pipeline
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Transactional outbox queue monitoring, exponential backoff retries, and dead-letter queue governance.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleTriggerDispatch}
            disabled={dispatching}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition shadow-xs disabled:opacity-50 cursor-pointer"
          >
            <Activity className={`w-3.5 h-3.5 ${dispatching ? 'animate-spin' : ''}`} />
            {dispatching ? 'Dispatching...' : 'Dispatch Outbox Now'}
          </button>
          <button
            onClick={fetchOutboxAndHealth}
            className="p-1.5 text-slate-500 hover:text-slate-800 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition shadow-xs cursor-pointer"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Health Overview Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-[10px] font-semibold uppercase text-slate-500">Pipeline Status</span>
          <div className="flex items-center gap-1.5 mt-1">
            <span
              className={`w-2 h-2 rounded-full ${
                health?.status === 'HEALTHY' ? 'bg-emerald-500' : 'bg-rose-500'
              }`}
            />
            <span className="text-sm font-bold text-slate-900">{health?.status || 'UNKNOWN'}</span>
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-[10px] font-semibold uppercase text-slate-500">Pending Outbox</span>
          <div className="text-lg font-bold text-slate-900 font-mono mt-1">
            {health?.pending_outbox_count ?? 0}
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-rose-200 bg-rose-50/20 shadow-xs">
          <span className="text-[10px] font-semibold uppercase text-rose-700">Dead Letter Queue</span>
          <div className="text-lg font-bold text-rose-700 font-mono mt-1">
            {health?.dead_letter_count ?? 0}
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-emerald-200 bg-emerald-50/20 shadow-xs">
          <span className="text-[10px] font-semibold uppercase text-emerald-700">Delivered 24h</span>
          <div className="text-lg font-bold text-emerald-700 font-mono mt-1">
            {health?.total_delivered_24h ?? 0}
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-[10px] font-semibold uppercase text-slate-500">Failed 24h</span>
          <div className="text-lg font-bold text-slate-700 font-mono mt-1">
            {health?.total_failed_24h ?? 0}
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-[10px] font-semibold uppercase text-slate-500">Email Mode</span>
          <div className="text-xs font-bold text-indigo-700 truncate mt-1">
            {health?.email_mode || 'MOCK_LOCAL'}
          </div>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1">
            <span className="text-slate-500 font-medium">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-transparent font-semibold text-slate-800 focus:outline-none cursor-pointer"
            >
              <option value="">All Statuses</option>
              <option value="PENDING">Pending</option>
              <option value="PROCESSING">Processing</option>
              <option value="RETRYING">Retrying (Backoff)</option>
              <option value="DELIVERED">Delivered</option>
              <option value="DEAD_LETTERED">Dead Letter Queue (DLQ)</option>
              <option value="FAILED">Failed</option>
            </select>
          </div>

          <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1">
            <span className="text-slate-500 font-medium">Channel:</span>
            <select
              value={channelFilter}
              onChange={(e) => setChannelFilter(e.target.value)}
              className="bg-transparent font-semibold text-slate-800 focus:outline-none cursor-pointer"
            >
              <option value="">All Channels</option>
              <option value="EMAIL">Email</option>
              <option value="WEBHOOK">Webhook</option>
              <option value="IN_APP">In-App</option>
              <option value="SLACK">Slack</option>
              <option value="TEAMS">Teams</option>
            </select>
          </div>
        </div>

        <span className="text-slate-500 font-medium">Showing {outboxItems.length} records</span>
      </div>

      {/* Outbox Items Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-600">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 uppercase font-semibold text-[10px] tracking-wider">
              <tr>
                <th className="py-3 px-4">Subject</th>
                <th className="py-3 px-4">Channel</th>
                <th className="py-3 px-4">Recipient</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Attempts</th>
                <th className="py-3 px-4">Next Attempt</th>
                <th className="py-3 px-4">Error Message</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    <div className="w-6 h-6 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                    Loading outbox records...
                  </td>
                </tr>
              ) : outboxItems.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    No records found in transactional outbox.
                  </td>
                </tr>
              ) : (
                outboxItems.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50 transition">
                    <td className="py-3 px-4 max-w-xs">
                      <div className="font-semibold text-slate-900 truncate" title={item.subject}>
                        {item.subject}
                      </div>
                      <div className="text-[10px] text-slate-400 font-mono truncate">{item.id}</div>
                    </td>

                    <td className="py-3 px-4">
                      <span className="font-bold text-slate-700 bg-slate-100 px-2 py-0.5 rounded text-[10px]">
                        {item.channel}
                      </span>
                    </td>

                    <td className="py-3 px-4 font-mono text-slate-700 max-w-xs truncate" title={item.recipient}>
                      {item.recipient}
                    </td>

                    <td className="py-3 px-4">
                      <span
                        className={`inline-block px-2 py-0.5 text-[10px] font-bold rounded-full border ${getStatusBadgeClass(
                          item.status
                        )}`}
                      >
                        {item.status}
                      </span>
                    </td>

                    <td className="py-3 px-4 font-mono">
                      {item.attempts} / {item.max_attempts}
                    </td>

                    <td className="py-3 px-4 text-slate-500 text-[11px]">
                      {new Date(item.next_attempt_at).toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </td>

                    <td className="py-3 px-4 text-rose-600 max-w-xs truncate" title={item.last_error || ''}>
                      {item.last_error || <span className="text-slate-300">-</span>}
                    </td>

                    <td className="py-3 px-4 text-right space-x-1">
                      {(item.status === 'DEAD_LETTERED' || item.status === 'FAILED') && (
                        <button
                          onClick={() => handleRetry(item.id)}
                          className="inline-flex items-center gap-1 px-2 py-1 text-[11px] font-semibold text-blue-700 bg-blue-50 border border-blue-200 rounded hover:bg-blue-100 transition cursor-pointer"
                        >
                          <RotateCcw className="w-3 h-3" />
                          Retry
                        </button>
                      )}

                      {(item.status === 'PENDING' || item.status === 'RETRYING') && (
                        <button
                          onClick={() => handleCancel(item.id)}
                          className="inline-flex items-center gap-1 px-2 py-1 text-[11px] font-semibold text-red-700 bg-red-50 border border-red-200 rounded hover:bg-red-100 transition cursor-pointer"
                        >
                          <Ban className="w-3 h-3" />
                          Cancel
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
    </div>
  );
};
