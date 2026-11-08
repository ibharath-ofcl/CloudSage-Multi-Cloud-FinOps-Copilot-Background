import React from 'react';

interface BatchReviewToolbarProps {
  selectedCount: number;
  onClearSelection: () => void;
  onAction: (action: 'APPROVE' | 'REJECT' | 'DISMISS' | 'SNOOZE' | 'ENDORSE') => void;
  isWasteMode?: boolean;
}

export const BatchReviewToolbar: React.FC<BatchReviewToolbarProps> = ({
  selectedCount,
  onClearSelection,
  onAction,
  isWasteMode = false,
}) => {
  if (selectedCount === 0) return null;

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 bg-slate-900 border border-indigo-500/40 shadow-2xl rounded-2xl px-6 py-3 flex items-center space-x-4 animate-in fade-in slide-in-from-bottom-4 duration-200">
      <div className="flex items-center space-x-2">
        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-indigo-600 text-xs font-bold text-white">
          {selectedCount}
        </span>
        <span className="text-sm font-medium text-slate-200">
          {selectedCount === 1 ? 'item selected' : 'items selected'}
        </span>
      </div>

      <div className="h-5 w-px bg-slate-700" />

      {isWasteMode ? (
        <div className="flex items-center space-x-2">
          <button
            onClick={() => onAction('APPROVE')} // in waste context represents Acknowledge
            className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium rounded-lg transition"
          >
            Acknowledge
          </button>
          <button
            onClick={() => onAction('SNOOZE')}
            className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-slate-200 text-xs font-medium rounded-lg transition"
          >
            Snooze
          </button>
          <button
            onClick={() => onAction('DISMISS')}
            className="px-3 py-1.5 bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 text-xs font-medium rounded-lg transition"
          >
            Dismiss
          </button>
        </div>
      ) : (
        <div className="flex items-center space-x-2">
          <button
            onClick={() => onAction('APPROVE')}
            className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium rounded-lg transition"
          >
            Batch Approve
          </button>
          <button
            onClick={() => onAction('ENDORSE')}
            className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg transition"
          >
            Batch Endorse
          </button>
          <button
            onClick={() => onAction('SNOOZE')}
            className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-slate-200 text-xs font-medium rounded-lg transition"
          >
            Snooze
          </button>
          <button
            onClick={() => onAction('DISMISS')}
            className="px-3 py-1.5 bg-amber-600/20 hover:bg-amber-600/30 text-amber-300 text-xs font-medium rounded-lg transition"
          >
            Dismiss
          </button>
          <button
            onClick={() => onAction('REJECT')}
            className="px-3 py-1.5 bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 text-xs font-medium rounded-lg transition"
          >
            Reject
          </button>
        </div>
      )}

      <div className="h-5 w-px bg-slate-700" />

      <button
        onClick={onClearSelection}
        className="text-xs text-slate-400 hover:text-slate-200 transition"
      >
        Clear
      </button>
    </div>
  );
};
