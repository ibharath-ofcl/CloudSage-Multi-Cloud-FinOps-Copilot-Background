import React, { useEffect, useState } from 'react';
import {
  Bell,
  Mail,
  Moon,
  Clock,
  Shield,
  Save,
  Check,
  ArrowLeft,
  AlertTriangle,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { NotificationService } from '../services/api';
import { NotificationPreference } from '../types/alerts';

export const NotificationPreferencesPage: React.FC = () => {
  const [pref, setPref] = useState<NotificationPreference | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [saveSuccess, setSaveSuccess] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  // Form states
  const [enabledChannels, setEnabledChannels] = useState<string[]>(['IN_APP', 'EMAIL']);
  const [minSeverity, setMinSeverity] = useState<string>('LOW');
  const [receiveDigests, setReceiveDigests] = useState<boolean>(true);
  const [digestFrequency, setDigestFrequency] = useState<'IMMEDIATE' | 'DAILY' | 'WEEKLY'>('DAILY');
  const [quietHoursEnabled, setQuietHoursEnabled] = useState<boolean>(false);
  const [quietHoursStart, setQuietHoursStart] = useState<string>('22:00');
  const [quietHoursEnd, setQuietHoursEnd] = useState<string>('08:00');

  useEffect(() => {
    setLoading(true);
    NotificationService.getPreferences()
      .then((res) => {
        setPref(res);
        setEnabledChannels(res.enabled_channels || ['IN_APP', 'EMAIL']);
        setMinSeverity(res.min_severity || 'LOW');
        setReceiveDigests(res.receive_digests ?? true);
        setDigestFrequency((res.digest_frequency as any) || 'DAILY');
        setQuietHoursEnabled(res.quiet_hours_enabled ?? false);
        setQuietHoursStart(res.quiet_hours_start_utc || '22:00');
        setQuietHoursEnd(res.quiet_hours_end_utc || '08:00');
      })
      .catch((err) => {
        console.error('Failed to load preferences', err);
        setError('Failed to load preferences.');
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  const handleToggleChannel = (ch: string) => {
    setEnabledChannels((prev) =>
      prev.includes(ch) ? prev.filter((c) => c !== ch) : [...prev, ch]
    );
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSaveSuccess(false);

    try {
      const updated = await NotificationService.updatePreferences({
        enabled_channels: enabledChannels,
        min_severity: minSeverity,
        receive_digests: receiveDigests,
        digest_frequency: digestFrequency,
        quiet_hours_enabled: quietHoursEnabled,
        quiet_hours_start_utc: quietHoursStart,
        quiet_hours_end_utc: quietHoursEnd,
      });
      setPref(updated);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 4000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save notification preferences.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="p-12 text-center text-slate-400 flex flex-col items-center justify-center min-h-[50vh]">
        <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mb-3" />
        <span className="text-xs">Loading preferences...</span>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 max-w-4xl mx-auto text-xs">
      {/* Header */}
      <div>
        <button
          onClick={() => navigate('/alerts')}
          className="inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 font-semibold mb-2 cursor-pointer"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to Alerts Hub
        </button>
        <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
          <Bell className="w-5 h-5 text-blue-600" />
          Personal Notification & Alert Preferences
        </h1>
        <p className="text-xs text-slate-500 mt-1">
          Customize delivery channels, minimum alert severity, quiet hours, and daily FinOps digest cadences.
        </p>
      </div>

      {saveSuccess && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 flex items-center gap-2 font-medium">
          <Check className="w-4 h-4 text-emerald-600" />
          Preferences saved successfully!
        </div>
      )}

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-red-800 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-red-600" />
          {error}
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-6">
        {/* Delivery Channels */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-5 space-y-4">
          <h2 className="font-bold text-slate-900 text-sm flex items-center gap-1.5">
            <Mail className="w-4 h-4 text-indigo-600" />
            Active Delivery Channels
          </h2>
          <p className="text-slate-500 text-[11px]">
            Choose where CloudSage sends alerts matching your role and subscription rules.
          </p>

          <div className="space-y-3">
            <label className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg border border-slate-200 cursor-pointer hover:bg-slate-100/60 transition">
              <input
                type="checkbox"
                checked={enabledChannels.includes('IN_APP')}
                onChange={() => handleToggleChannel('IN_APP')}
                className="rounded text-blue-600 focus:ring-blue-500 w-4 h-4"
              />
              <div>
                <p className="font-semibold text-slate-900">In-App Notification Center</p>
                <p className="text-[11px] text-slate-500">
                  Real-time bell badge and notifications list inside CloudSage.
                </p>
              </div>
            </label>

            <label className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg border border-slate-200 cursor-pointer hover:bg-slate-100/60 transition">
              <input
                type="checkbox"
                checked={enabledChannels.includes('EMAIL')}
                onChange={() => handleToggleChannel('EMAIL')}
                className="rounded text-blue-600 focus:ring-blue-500 w-4 h-4"
              />
              <div>
                <p className="font-semibold text-slate-900">Email Notifications</p>
                <p className="text-[11px] text-slate-500">
                  Transactional alert emails sent to: <span className="font-mono text-slate-700">{pref?.user_email}</span>
                </p>
              </div>
            </label>
          </div>
        </div>

        {/* Severity Threshold */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-5 space-y-4">
          <h2 className="font-bold text-slate-900 text-sm flex items-center gap-1.5">
            <Shield className="w-4 h-4 text-rose-600" />
            Minimum Severity Threshold
          </h2>
          <p className="text-slate-500 text-[11px]">
            Only notify me for anomalies meeting or exceeding this severity level.
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].map((sev) => (
              <button
                key={sev}
                type="button"
                onClick={() => setMinSeverity(sev)}
                className={`p-3 rounded-xl border text-center transition cursor-pointer font-bold uppercase ${
                  minSeverity === sev
                    ? 'bg-blue-50 border-blue-600 text-blue-700 shadow-xs'
                    : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                }`}
              >
                {sev}
              </button>
            ))}
          </div>
        </div>

        {/* Quiet Hours */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-bold text-slate-900 text-sm flex items-center gap-1.5">
              <Moon className="w-4 h-4 text-purple-600" />
              Quiet Hours (Non-Critical Suppressed)
            </h2>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={quietHoursEnabled}
                onChange={(e) => setQuietHoursEnabled(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-9 h-5 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-purple-600" />
            </label>
          </div>

          <p className="text-slate-500 text-[11px]">
            When enabled, Low and Medium severity alerts are held in outbox during your quiet hours and delivered next morning. Critical anomalies always bypass quiet hours.
          </p>

          {quietHoursEnabled && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Start Time (UTC)</label>
                <input
                  type="time"
                  value={quietHoursStart}
                  onChange={(e) => setQuietHoursStart(e.target.value)}
                  className="w-full p-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none"
                />
              </div>
              <div>
                <label className="block font-semibold text-slate-700 mb-1">End Time (UTC)</label>
                <input
                  type="time"
                  value={quietHoursEnd}
                  onChange={(e) => setQuietHoursEnd(e.target.value)}
                  className="w-full p-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none"
                />
              </div>
            </div>
          )}
        </div>

        {/* Digest Cadence */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-bold text-slate-900 text-sm flex items-center gap-1.5">
              <Clock className="w-4 h-4 text-amber-600" />
              Summary Digest Delivery
            </h2>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={receiveDigests}
                onChange={(e) => setReceiveDigests(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-9 h-5 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-amber-600" />
            </label>
          </div>

          {receiveDigests && (
            <div className="space-y-2 pt-2">
              <span className="font-semibold text-slate-700 block mb-1">Digest Frequency</span>
              <div className="grid grid-cols-3 gap-3">
                {(['IMMEDIATE', 'DAILY', 'WEEKLY'] as const).map((freq) => (
                  <button
                    key={freq}
                    type="button"
                    onClick={() => setDigestFrequency(freq)}
                    className={`p-2.5 rounded-xl border text-center transition cursor-pointer font-bold text-[11px] ${
                      digestFrequency === freq
                        ? 'bg-amber-50 border-amber-600 text-amber-800'
                        : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                    }`}
                  >
                    {freq}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Submit */}
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={saving}
            className="inline-flex items-center gap-2 px-6 py-2.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-xl transition shadow-xs disabled:opacity-50 cursor-pointer"
          >
            <Save className="w-4 h-4" />
            {saving ? 'Saving...' : 'Save Preferences'}
          </button>
        </div>
      </form>
    </div>
  );
};
