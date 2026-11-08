import React from 'react';
import { RecommendationHistoryItem } from '../types/workspace';

interface AuditTimelineProps {
  historyItems: RecommendationHistoryItem[];
}

export const AuditTimeline: React.FC<AuditTimelineProps> = ({ historyItems }) => {
  if (!historyItems || historyItems.length === 0) {
    return (
      <div className="bg-slate-800/60 rounded-xl p-5 border border-slate-700/60 text-center text-xs text-slate-400">
        No state transition history recorded.
      </div>
    );
  }

  // Sort chronological descending
  const sorted = [...historyItems].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

  return (
    <div className="bg-slate-800/60 rounded-xl p-5 border border-slate-700/60">
      <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-4">
        Lifecycle Transition Audit Trail
      </h4>

      <div className="relative pl-6 space-y-4 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-700">
        {sorted.map((item) => (
          <div key={item.id} className="relative">
            {/* Timeline bullet */}
            <div className="absolute -left-6 top-1 w-3 h-3 rounded-full border-2 border-slate-900 bg-indigo-500" />

            <div className="bg-slate-900/60 rounded-lg p-3 border border-slate-800">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-slate-200">
                  {item.action.replace(/_/g, ' ')}
                </span>
                <span className="text-[10px] text-slate-500 font-mono">
                  {new Date(item.created_at).toLocaleString()}
                </span>
              </div>

              {item.from_status && (
                <div className="text-[11px] text-slate-400 mt-1 font-mono">
                  State transition: <span className="text-slate-300">{item.from_status}</span> → <span className="text-indigo-400 font-semibold">{item.to_status}</span>
                </div>
              )}

              {item.actor && (
                <div className="text-[10px] text-slate-500 mt-1">
                  Actor: <span className="text-slate-300 font-mono">{item.actor}</span>
                </div>
              )}

              {item.notes && (
                <div className="mt-2 text-xs text-slate-300 bg-slate-950 p-2 rounded border border-slate-800/80 italic">
                  "{item.notes}"
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
