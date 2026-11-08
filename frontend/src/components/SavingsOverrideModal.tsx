import React, { useState, useEffect } from 'react';
import { SavingsOverrideItem } from '../types/workspace';
import { WorkspaceService } from '../services/api';

interface SavingsOverrideModalProps {
  isOpen: boolean;
  recommendationId: string;
  currentSavings: number;
  onClose: () => void;
  onSuccess: () => void;
}

export const SavingsOverrideModal: React.FC<SavingsOverrideModalProps> = ({
  isOpen,
  recommendationId,
  currentSavings,
  onClose,
  onSuccess,
}) => {
  const [proposedSavings, setProposedSavings] = useState<string>(currentSavings.toString());
  const [reason, setReason] = useState<string>('');
  const [proposer, setProposer] = useState<string>('finops.lead@enterprise.com');
  const [overrides, setOverrides] = useState<SavingsOverrideItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    if (isOpen && recommendationId) {
      loadOverrides();
    }
  }, [isOpen, recommendationId]);

  const loadOverrides = async () => {
    try {
      const data = await WorkspaceService.listSavingsOverrides(recommendationId);
      setOverrides(data || []);
    } catch (err) {
      console.error('Failed to load overrides', err);
    }
  };

  if (!isOpen) return null;

  const handlePropose = async () => {
    const val = parseFloat(proposedSavings);
    if (isNaN(val) || val < 0) {
      setError('Please provide a valid non-negative savings figure.');
      return;
    }
    if (!reason.trim()) {
      setError('A documented engineering/FinOps justification is mandatory.');
      return;
    }

    setLoading(true);
    setError('');
    try {
      await WorkspaceService.proposeSavingsOverride(recommendationId, {
        proposed_monthly_savings: val,
        reason: reason.trim(),
        proposed_by: proposer.trim() || 'finops.lead@enterprise.com',
      });
      setReason('');
      await loadOverrides();
      onSuccess();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to submit savings override proposal.');
    } finally {
      setLoading(false);
    }
  };

  const handleReview = async (overrideId: string, approved: boolean) => {
    setLoading(true);
    setError('');
    try {
      await WorkspaceService.approveSavingsOverride(recommendationId, overrideId, {
        approved,
        approved_by: 'finops.manager@enterprise.com',
        rejection_reason: approved ? undefined : 'Rejected by FinOps management review.',
      });
      await loadOverrides();
      onSuccess();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to review override.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl w-full max-w-lg p-6 shadow-2xl animate-in zoom-in-95 duration-150 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div>
            <h3 className="text-base font-semibold text-slate-100">Savings Override Governance</h3>
            <p className="text-xs text-slate-400">Formal human-in-the-loop adjustment with dual custody tracking</p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-200">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {error && (
          <div className="mt-3 p-2.5 bg-rose-500/10 border border-rose-500/30 rounded-lg text-xs text-rose-300">
            {error}
          </div>
        )}

        {/* Current vs Proposed Baseline */}
        <div className="mt-4 p-3 bg-slate-800/60 rounded-xl border border-slate-700/60 flex items-center justify-between">
          <div>
            <div className="text-[11px] text-slate-400">Algorithmic Baseline</div>
            <div className="text-base font-bold text-slate-200">${currentSavings.toFixed(2)} USD/mo</div>
          </div>
          <div className="text-right">
            <div className="text-[11px] text-slate-400">Annualized Baseline</div>
            <div className="text-sm font-semibold text-slate-300">${(currentSavings * 12).toFixed(2)} USD/yr</div>
          </div>
        </div>

        {/* Proposal Form */}
        <div className="mt-4 space-y-3">
          <h4 className="text-xs font-semibold text-indigo-300 uppercase tracking-wider">Propose Adjustment</h4>
          
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Proposed Monthly Savings ($) <span className="text-rose-400">*</span>
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={proposedSavings}
                onChange={(e) => setProposedSavings(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 font-mono"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Proposer Identity</label>
              <input
                type="text"
                value={proposer}
                onChange={(e) => setProposer(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Engineering / Financial Justification <span className="text-rose-400">*</span>
            </label>
            <textarea
              rows={2}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. Account has enterprise discount agreement (EDP) applied..."
              className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 placeholder-slate-500"
            />
          </div>

          <button
            onClick={handlePropose}
            disabled={loading}
            className="w-full py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg transition disabled:opacity-50"
          >
            Submit Proposal for Review
          </button>
        </div>

        {/* Existing Overrides & History */}
        {overrides.length > 0 && (
          <div className="mt-6 border-t border-slate-800 pt-4">
            <h4 className="text-xs font-semibold text-slate-300 mb-2">Proposal Audit Trail</h4>
            <div className="space-y-2">
              {overrides.map((item) => (
                <div key={item.id} className="p-3 bg-slate-800/40 rounded-lg border border-slate-800 flex items-center justify-between">
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                        item.status === 'APPROVED' ? 'bg-emerald-500/20 text-emerald-400' :
                        item.status === 'REJECTED' ? 'bg-rose-500/20 text-rose-400' : 'bg-amber-500/20 text-amber-400'
                      }`}>
                        {item.status}
                      </span>
                      <span className="text-xs font-mono font-semibold text-slate-200">
                        ${item.proposed_monthly_savings} USD/mo
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 mt-1">{item.reason}</p>
                    <div className="text-[10px] text-slate-500 mt-0.5">By {item.proposed_by}</div>
                  </div>

                  {item.status === 'PROPOSED' && (
                    <div className="flex items-center space-x-1.5">
                      <button
                        onClick={() => handleReview(item.id, true)}
                        className="px-2 py-1 bg-emerald-600/30 hover:bg-emerald-600/50 text-emerald-300 text-[11px] rounded transition"
                      >
                        Approve
                      </button>
                      <button
                        onClick={() => handleReview(item.id, false)}
                        className="px-2 py-1 bg-rose-600/30 hover:bg-rose-600/50 text-rose-300 text-[11px] rounded transition"
                      >
                        Reject
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
