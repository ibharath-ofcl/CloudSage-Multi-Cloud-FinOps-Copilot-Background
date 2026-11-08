import React, { useEffect, useState } from 'react';
import {
  Sliders,
  Plus,
  Play,
  Edit2,
  Trash2,
  Check,
  AlertTriangle,
  X,
  Search,
  ArrowLeft,
  ShieldCheck,
  Globe,
  Bell,
  Mail,
  Webhook,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { AlertService } from '../services/api';
import {
  AlertRule,
  AlertRuleCreate,
  AlertRulePreviewResponse,
  AlertSeverity,
  NotificationChannelType,
} from '../types/alerts';

export const AlertRuleManagementPage: React.FC = () => {
  const [rules, setRules] = useState<AlertRule[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [providerFilter, setProviderFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const navigate = useNavigate();

  // Create / Edit Modal State
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [editingRuleId, setEditingRuleId] = useState<string | null>(null);
  const [formData, setFormData] = useState<AlertRuleCreate>({
    name: '',
    description: '',
    provider: 'ALL',
    account_id: '',
    region: '',
    service_name: '',
    min_severity: 'MEDIUM',
    min_excess_cost: 100,
    percentage_deviation_threshold: 25,
    cooldown_minutes: 1440,
    channels: ['IN_APP', 'EMAIL'],
    recipients: [],
    is_enabled: true,
  });
  const [recipientInput, setRecipientInput] = useState<string>('');
  const [saving, setSaving] = useState<boolean>(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Dry-Run Preview State
  const [previewData, setPreviewData] = useState<AlertRulePreviewResponse | null>(null);
  const [isPreviewing, setIsPreviewing] = useState<boolean>(false);

  const fetchRules = async () => {
    setLoading(true);
    try {
      const res = await AlertService.listRules({
        provider: providerFilter || undefined,
        search: searchQuery || undefined,
      });
      setRules(res.items || []);
    } catch (err) {
      console.error('Failed to load alert rules', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRules();
  }, [providerFilter]);

  const handleOpenCreateModal = () => {
    setEditingRuleId(null);
    setFormData({
      name: '',
      description: '',
      provider: 'ALL',
      account_id: '',
      region: '',
      service_name: '',
      min_severity: 'MEDIUM',
      min_excess_cost: 100,
      percentage_deviation_threshold: 25,
      cooldown_minutes: 1440,
      channels: ['IN_APP', 'EMAIL'],
      recipients: ['finops-team@cloudsage.internal'],
      is_enabled: true,
    });
    setRecipientInput('');
    setPreviewData(null);
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleOpenEditModal = (rule: AlertRule) => {
    setEditingRuleId(rule.id);
    setFormData({
      name: rule.name,
      description: rule.description || '',
      provider: rule.provider,
      account_id: rule.account_id || '',
      region: rule.region || '',
      service_name: rule.service_name || '',
      min_severity: rule.min_severity,
      min_excess_cost: Number(rule.min_excess_cost),
      percentage_deviation_threshold: Number(rule.percentage_deviation_threshold),
      cooldown_minutes: rule.cooldown_minutes,
      channels: rule.channels,
      recipients: rule.recipients || [],
      is_enabled: rule.is_enabled,
    });
    setRecipientInput('');
    setPreviewData(null);
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleToggleRule = async (ruleId: string) => {
    try {
      const updated = await AlertService.toggleRule(ruleId);
      setRules((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
    } catch (err) {
      console.error('Failed to toggle rule', err);
    }
  };

  const handleDeleteRule = async (ruleId: string) => {
    if (!window.confirm('Are you sure you want to delete this alert rule?')) return;
    try {
      await AlertService.deleteRule(ruleId);
      setRules((prev) => prev.filter((r) => r.id !== ruleId));
    } catch (err) {
      console.error('Failed to delete rule', err);
    }
  };

  const handleRunPreview = async () => {
    setIsPreviewing(true);
    try {
      const res = await AlertService.previewRule({
        provider: formData.provider,
        account_id: formData.account_id || undefined,
        min_severity: formData.min_severity,
        min_excess_cost: formData.min_excess_cost,
        percentage_deviation_threshold: formData.percentage_deviation_threshold,
      });
      setPreviewData(res);
    } catch (err) {
      console.error('Failed to preview rule', err);
    } finally {
      setIsPreviewing(false);
    }
  };

  const handleAddRecipient = () => {
    if (!recipientInput.trim()) return;
    setFormData((prev) => ({
      ...prev,
      recipients: [...(prev.recipients || []), recipientInput.trim()],
    }));
    setRecipientInput('');
  };

  const handleRemoveRecipient = (idx: number) => {
    setFormData((prev) => ({
      ...prev,
      recipients: (prev.recipients || []).filter((_, i) => i !== idx),
    }));
  };

  const handleToggleChannel = (ch: NotificationChannelType) => {
    setFormData((prev) => {
      const current = prev.channels || [];
      if (current.includes(ch)) {
        return { ...prev, channels: current.filter((c) => c !== ch) };
      } else {
        return { ...prev, channels: [...current, ch] };
      }
    });
  };

  const handleSaveRule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      setFormError('Rule name is required.');
      return;
    }

    setSaving(true);
    setFormError(null);
    try {
      if (editingRuleId) {
        const updated = await AlertService.updateRule(editingRuleId, formData);
        setRules((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
      } else {
        const created = await AlertService.createRule(formData);
        setRules((prev) => [created, ...prev]);
      }
      setIsModalOpen(false);
    } catch (err: any) {
      setFormError(err.response?.data?.detail || 'Failed to save alert rule.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
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
            <Sliders className="w-5 h-5 text-indigo-600" />
            Alert Rule Governance Engine
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Define multi-dimensional thresholds, cooldown windows, and delivery routing across AWS, Azure, and GCP.
          </p>
        </div>

        <button
          onClick={handleOpenCreateModal}
          className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition shadow-xs cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          Create Alert Rule
        </button>
      </div>

      {/* Rules Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3 text-xs bg-slate-50/50">
          <div className="flex items-center gap-2">
            <span className="text-slate-500 font-medium">Provider Scope:</span>
            <select
              value={providerFilter}
              onChange={(e) => setProviderFilter(e.target.value)}
              className="p-1 bg-white border border-slate-200 rounded font-semibold text-slate-800 focus:outline-none cursor-pointer"
            >
              <option value="">All Rules</option>
              <option value="AWS">AWS Rules</option>
              <option value="AZURE">Azure Rules</option>
              <option value="GCP">GCP Rules</option>
              <option value="ALL">Multi-Cloud (ALL)</option>
            </select>
          </div>

          <div className="relative w-full sm:w-64">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search rule name..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && fetchRules()}
              className="w-full pl-8 pr-3 py-1 text-xs bg-white border border-slate-200 rounded focus:outline-none text-slate-800"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-600">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 uppercase font-semibold text-[10px] tracking-wider">
              <tr>
                <th className="py-3 px-4">Rule Name</th>
                <th className="py-3 px-4">Cloud Scope</th>
                <th className="py-3 px-4">Thresholds</th>
                <th className="py-3 px-4">Min Severity</th>
                <th className="py-3 px-4">Channels</th>
                <th className="py-3 px-4">Cooldown</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    <div className="w-6 h-6 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                    Loading alert rules...
                  </td>
                </tr>
              ) : rules.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    No alert rules configured. Click &quot;Create Alert Rule&quot; to build your first rule.
                  </td>
                </tr>
              ) : (
                rules.map((rule) => (
                  <tr key={rule.id} className="hover:bg-slate-50 transition">
                    <td className="py-3.5 px-4 max-w-xs">
                      <div className="font-semibold text-slate-900">{rule.name}</div>
                      {rule.description && (
                        <div className="text-[11px] text-slate-400 truncate">{rule.description}</div>
                      )}
                    </td>

                    <td className="py-3.5 px-4">
                      <span className="font-semibold text-slate-700 bg-slate-100 px-2 py-0.5 rounded text-[10px]">
                        {rule.provider}
                      </span>
                      {rule.service_name && (
                        <div className="text-[11px] text-slate-500 mt-0.5">{rule.service_name}</div>
                      )}
                    </td>

                    <td className="py-3.5 px-4 font-mono">
                      <div>${Number(rule.min_excess_cost).toLocaleString()} excess</div>
                      <div className="text-[10px] text-slate-400">+{Number(rule.percentage_deviation_threshold)}% deviation</div>
                    </td>

                    <td className="py-3.5 px-4">
                      <span className="px-1.5 py-0.5 text-[9px] font-bold rounded uppercase bg-slate-100 text-slate-700 border border-slate-200">
                        {rule.min_severity}
                      </span>
                    </td>

                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-1 flex-wrap">
                        {rule.channels.map((ch) => (
                          <span
                            key={ch}
                            className="px-1.5 py-0.5 bg-blue-50 text-blue-700 rounded text-[9px] font-medium"
                          >
                            {ch}
                          </span>
                        ))}
                      </div>
                    </td>

                    <td className="py-3.5 px-4 text-slate-500 font-mono text-[11px]">
                      {rule.cooldown_minutes}m ({Math.round(rule.cooldown_minutes / 60)}h)
                    </td>

                    <td className="py-3.5 px-4">
                      <button
                        onClick={() => handleToggleRule(rule.id)}
                        className={`px-2 py-0.5 text-[10px] font-semibold rounded-full border transition cursor-pointer ${
                          rule.is_enabled
                            ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                            : 'bg-slate-100 text-slate-500 border-slate-300'
                        }`}
                      >
                        {rule.is_enabled ? 'Active' : 'Disabled'}
                      </button>
                    </td>

                    <td className="py-3.5 px-4 text-right space-x-1">
                      <button
                        onClick={() => handleOpenEditModal(rule)}
                        className="p-1 text-slate-400 hover:text-slate-700 rounded transition cursor-pointer"
                        title="Edit Rule"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleDeleteRule(rule.id)}
                        className="p-1 text-slate-400 hover:text-red-600 rounded transition cursor-pointer"
                        title="Delete Rule"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create / Edit Rule Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 overflow-y-auto">
          <div className="bg-white rounded-xl border border-slate-200 shadow-2xl w-full max-w-2xl my-8 overflow-hidden text-xs">
            <div className="px-6 py-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
              <div>
                <h3 className="font-bold text-slate-900 text-sm">
                  {editingRuleId ? 'Edit Alert Rule' : 'Create Alert Rule'}
                </h3>
                <p className="text-[11px] text-slate-500">
                  Configure trigger criteria, financial thresholds, and notifications
                </p>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSaveRule} className="p-6 space-y-4">
              {formError && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-xs">
                  {formError}
                </div>
              )}

              {/* Basic Info */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Rule Name *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Critical AWS EC2 Spike Alert"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full p-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Provider Scope</label>
                  <select
                    value={formData.provider}
                    onChange={(e) => setFormData({ ...formData, provider: e.target.value })}
                    className="w-full p-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500 font-semibold"
                  >
                    <option value="ALL">All Clouds (Multi-Cloud)</option>
                    <option value="AWS">Amazon Web Services (AWS)</option>
                    <option value="AZURE">Microsoft Azure</option>
                    <option value="GCP">Google Cloud Platform (GCP)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Description</label>
                <input
                  type="text"
                  placeholder="Explains what this rule monitors and triage protocol"
                  value={formData.description || ''}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full p-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>

              {/* Thresholds */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 bg-slate-50/70 p-3.5 rounded-xl border border-slate-200">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Min Excess Cost ($)</label>
                  <input
                    type="number"
                    min="0"
                    step="10"
                    value={formData.min_excess_cost}
                    onChange={(e) => setFormData({ ...formData, min_excess_cost: Number(e.target.value) })}
                    className="w-full p-2 bg-white border border-slate-200 rounded-lg focus:outline-none font-mono"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Min Deviation (%)</label>
                  <input
                    type="number"
                    min="0"
                    step="5"
                    value={formData.percentage_deviation_threshold}
                    onChange={(e) => setFormData({ ...formData, percentage_deviation_threshold: Number(e.target.value) })}
                    className="w-full p-2 bg-white border border-slate-200 rounded-lg focus:outline-none font-mono"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Min Severity</label>
                  <select
                    value={formData.min_severity}
                    onChange={(e) => setFormData({ ...formData, min_severity: e.target.value as AlertSeverity })}
                    className="w-full p-2 bg-white border border-slate-200 rounded-lg focus:outline-none font-semibold"
                  >
                    <option value="LOW">Low</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="HIGH">High</option>
                    <option value="CRITICAL">Critical</option>
                  </select>
                </div>
              </div>

              {/* Scope & Cooldown */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Account Scope (Optional)</label>
                  <input
                    type="text"
                    placeholder="e.g. 123456789012"
                    value={formData.account_id || ''}
                    onChange={(e) => setFormData({ ...formData, account_id: e.target.value })}
                    className="w-full p-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none font-mono text-[11px]"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Service Scope (Optional)</label>
                  <input
                    type="text"
                    placeholder="e.g. Amazon Elastic Compute Cloud"
                    value={formData.service_name || ''}
                    onChange={(e) => setFormData({ ...formData, service_name: e.target.value })}
                    className="w-full p-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none text-[11px]"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Cooldown Window (Minutes)</label>
                  <input
                    type="number"
                    min="15"
                    max="43200"
                    step="60"
                    value={formData.cooldown_minutes}
                    onChange={(e) => setFormData({ ...formData, cooldown_minutes: Number(e.target.value) })}
                    className="w-full p-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none font-mono"
                  />
                </div>
              </div>

              {/* Notification Channels */}
              <div>
                <label className="block font-semibold text-slate-700 mb-2">Notification Channels</label>
                <div className="flex flex-wrap items-center gap-3">
                  {(['IN_APP', 'EMAIL', 'WEBHOOK', 'SLACK', 'TEAMS'] as NotificationChannelType[]).map((ch) => (
                    <label key={ch} className="inline-flex items-center gap-1.5 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formData.channels?.includes(ch) || false}
                        onChange={() => handleToggleChannel(ch)}
                        className="rounded text-blue-600 focus:ring-blue-500"
                      />
                      <span className="text-xs text-slate-700 font-medium">{ch}</span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Recipients */}
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Recipients (Emails, Webhooks, User IDs)
                </label>
                <div className="flex items-center gap-2 mb-2">
                  <input
                    type="text"
                    placeholder="e.g. alerts@company.com or https://api.corp.com/webhook"
                    value={recipientInput}
                    onChange={(e) => setRecipientInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddRecipient())}
                    className="flex-1 p-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none"
                  />
                  <button
                    type="button"
                    onClick={handleAddRecipient}
                    className="px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-lg cursor-pointer"
                  >
                    Add
                  </button>
                </div>

                <div className="flex flex-wrap items-center gap-1.5">
                  {formData.recipients?.map((r, idx) => (
                    <span
                      key={idx}
                      className="inline-flex items-center gap-1 px-2 py-0.5 bg-slate-100 border border-slate-200 rounded text-[11px] text-slate-700"
                    >
                      {r}
                      <button
                        type="button"
                        onClick={() => handleRemoveRecipient(idx)}
                        className="hover:text-red-600 cursor-pointer"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  ))}
                </div>
              </div>

              {/* Dry-Run Preview Panel */}
              <div className="border border-slate-200 rounded-xl p-3 bg-slate-50/50 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-700 flex items-center gap-1.5">
                    <Play className="w-3.5 h-3.5 text-blue-600" />
                    Dry-Run Rule Tester
                  </span>
                  <button
                    type="button"
                    onClick={handleRunPreview}
                    disabled={isPreviewing}
                    className="px-2.5 py-1 text-xs font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded transition cursor-pointer disabled:opacity-50"
                  >
                    {isPreviewing ? 'Testing...' : 'Test Against Historical Data'}
                  </button>
                </div>

                {previewData && (
                  <div className="mt-2 text-xs text-slate-700">
                    <div className="flex items-center gap-2 font-semibold text-emerald-700">
                      <Check className="w-4 h-4" />
                      Rule matched {previewData.matched_count} of {previewData.total_evaluated} evaluated anomalies.
                    </div>
                    {previewData.sample_matches.length > 0 && (
                      <div className="mt-2 space-y-1">
                        <span className="font-medium text-slate-500 text-[11px]">Sample Matched Anomalies:</span>
                        {previewData.sample_matches.slice(0, 3).map((m, idx) => (
                          <div key={idx} className="p-1.5 bg-white rounded border border-slate-200 flex items-center justify-between text-[11px]">
                            <span>{m.title}</span>
                            <span className="font-mono font-semibold text-rose-600">${Number(m.excess_cost).toFixed(2)}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Modal Buttons */}
              <div className="pt-3 flex items-center justify-end gap-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 text-xs text-slate-600 hover:text-slate-800 rounded-lg cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="px-5 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition shadow-xs disabled:opacity-50 cursor-pointer"
                >
                  {saving ? 'Saving Rule...' : editingRuleId ? 'Update Rule' : 'Create Rule'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
