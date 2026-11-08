import React, { useState } from 'react';

interface ReviewDecisionModalProps {
  isOpen: boolean;
  action: string;
  itemCount: number;
  onClose: () => void;
  onSubmit: (data: {
    reason?: string;
    snoozeDays?: number;
    assignedTo?: string;
    externalTicketRef?: string;
  }) => void;
}

export const ReviewDecisionModal: React.FC<ReviewDecisionModalProps> = ({
  isOpen,
  action,
  itemCount,
  onClose,
  onSubmit,
}) => {
  const [reason, setReason] = useState<string>('');
  const [snoozeDays, setSnoozeDays] = useState<number>(14);
  const [assignedTo, setAssignedTo] = useState<string>('');
  const [ticketRef, setTicketRef] = useState<string>('');
  const [error, setError] = useState<string>('');

  if (!isOpen) return null;

  const requiresReason = action === 'DISMISS' || action === 'REJECT';

  const handleConfirm = () => {
    if (requiresReason && !reason.trim()) {
      setError(`A clear justification reason is mandatory when performing ${action}.`);
      return;
    }
    setError('');
    onSubmit({
      reason: reason.trim() || undefined,
      snoozeDays: action === 'SNOOZE' ? snoozeDays : undefined,
      assignedTo: assignedTo.trim() || undefined,
      externalTicketRef: ticketRef.trim() || undefined,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl w-full max-w-md p-6 shadow-2xl animate-in zoom-in-95 duration-150">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <h3 className="text-base font-semibold text-slate-100">
            Confirm {action} ({itemCount} {itemCount === 1 ? 'item' : 'items'})
          </h3>
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

        <div className="mt-4 space-y-4">
          {action === 'SNOOZE' && (
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Snooze Duration (Days)
              </label>
              <select
                value={snoozeDays}
                onChange={(e) => setSnoozeDays(Number(e.target.value))}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
              >
                <option value={7}>7 Days (1 week)</option>
                <option value={14}>14 Days (2 weeks)</option>
                <option value={30}>30 Days (1 month)</option>
                <option value={60}>60 Days (2 months)</option>
                <option value={90}>90 Days (Quarterly review)</option>
              </select>
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Justification / Operational Notes {requiresReason && <span className="text-rose-400">*</span>}
            </label>
            <textarea
              rows={3}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder={requiresReason ? 'Mandatory reason for rejection or dismissal...' : 'Optional review notes...'}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 placeholder-slate-500"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Assign Owner
              </label>
              <input
                type="text"
                value={assignedTo}
                onChange={(e) => setAssignedTo(e.target.value)}
                placeholder="dev-lead@company.com"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 placeholder-slate-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                External Ticket
              </label>
              <input
                type="text"
                value={ticketRef}
                onChange={(e) => setTicketRef(e.target.value)}
                placeholder="FINOPS-4021"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 placeholder-slate-500"
              />
            </div>
          </div>
        </div>

        <div className="mt-6 flex justify-end space-x-3">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium rounded-lg transition"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg transition shadow-md shadow-indigo-600/30"
          >
            Confirm Action
          </button>
        </div>
      </div>
    </div>
  );
};
