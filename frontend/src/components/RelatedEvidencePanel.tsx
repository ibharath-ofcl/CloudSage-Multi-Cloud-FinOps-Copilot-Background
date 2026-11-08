import React, { useState, useEffect } from 'react';
import { EntityCorrelations } from '../types/workspace';
import { WorkspaceService } from '../services/api';

interface RelatedEvidencePanelProps {
  recommendationId?: string;
  resourceId?: string;
  wasteFindingId?: string;
}

export const RelatedEvidencePanel: React.FC<RelatedEvidencePanelProps> = ({
  recommendationId,
  resourceId,
  wasteFindingId,
}) => {
  const [data, setData] = useState<EntityCorrelations | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);

    const fetchCorrelations = async () => {
      try {
        let res: EntityCorrelations;
        if (recommendationId) {
          res = await WorkspaceService.getRecommendationCorrelations(recommendationId);
        } else if (wasteFindingId) {
          const inv = await WorkspaceService.getFindingInvestigation(wasteFindingId);
          res = inv.correlations;
        } else if (resourceId) {
          res = await WorkspaceService.getResourceCorrelations(resourceId);
        } else {
          setLoading(false);
          return;
        }

        if (isMounted) setData(res);
      } catch (err) {
        console.error('Failed to load correlations', err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchCorrelations();
    return () => {
      isMounted = false;
    };
  }, [recommendationId, resourceId, wasteFindingId]);

  if (loading) {
    return (
      <div className="bg-slate-800/60 rounded-xl p-6 border border-slate-700/60 flex items-center justify-center min-h-[180px]">
        <div className="text-slate-400 text-xs">Loading correlation matrix...</div>
      </div>
    );
  }

  if (!data) {
    return null;
  }

  const tax = data.financial_taxonomy;

  return (
    <div className="bg-slate-800/60 rounded-xl p-5 border border-slate-700/60 space-y-4">
      {/* Anti-double-counting Financial Separation */}
      <div className="p-4 bg-slate-900/80 rounded-xl border border-slate-800">
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-xs font-semibold text-indigo-300 uppercase tracking-wider">
            Financial Impact Taxonomy (Anti-Double-Counting)
          </h4>
          <span className="text-[10px] text-emerald-400 font-mono bg-emerald-500/10 px-2 py-0.5 rounded">
            Strict Separation
          </span>
        </div>

        <div className="grid grid-cols-4 gap-2 text-center">
          <div className="bg-slate-950 p-2 rounded border border-slate-800">
            <div className="text-[10px] text-slate-400">Baseline Spend</div>
            <div className="text-sm font-bold text-slate-200">${tax.baseline_monthly_spend.toFixed(2)}</div>
          </div>
          <div className="bg-slate-950 p-2 rounded border border-slate-800">
            <div className="text-[10px] text-amber-400">Monthly Waste</div>
            <div className="text-sm font-bold text-amber-400">${tax.active_monthly_waste.toFixed(2)}</div>
          </div>
          <div className="bg-slate-950 p-2 rounded border border-slate-800">
            <div className="text-[10px] text-indigo-400">Potential Savings</div>
            <div className="text-sm font-bold text-indigo-300">${tax.potential_monthly_savings.toFixed(2)}</div>
          </div>
          <div className="bg-slate-950 p-2 rounded border border-slate-800">
            <div className="text-[10px] text-emerald-400">Verified Realized</div>
            <div className="text-sm font-bold text-emerald-400">${tax.verified_realized_savings.toFixed(2)}</div>
          </div>
        </div>

        <p className="text-[11px] text-slate-400 mt-2 italic">
          {tax.anti_double_counting_note}
        </p>
      </div>

      {/* Correlated Entities Matrix */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {/* Waste Findings */}
        <div className="bg-slate-900/60 rounded-lg p-3 border border-slate-800">
          <div className="text-xs font-semibold text-slate-300 mb-2 flex items-center justify-between">
            <span>Correlated Waste ({data.waste_findings.length})</span>
          </div>
          {data.waste_findings.length === 0 ? (
            <div className="text-[11px] text-slate-500 italic">No open waste detections.</div>
          ) : (
            <div className="space-y-1.5 max-h-40 overflow-y-auto">
              {data.waste_findings.map((w) => (
                <div key={w.id} className="text-[11px] p-2 bg-slate-950/60 rounded border border-slate-800/80 flex items-center justify-between">
                  <div>
                    <span className="font-semibold text-slate-300">{w.finding_title || w.waste_type}</span>
                    <span className="ml-2 text-[10px] text-slate-500 font-mono">[{w.status}]</span>
                  </div>
                  <span className="font-mono text-amber-400">${w.estimated_monthly_waste}/mo</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Cost Anomalies */}
        <div className="bg-slate-900/60 rounded-lg p-3 border border-slate-800">
          <div className="text-xs font-semibold text-slate-300 mb-2 flex items-center justify-between">
            <span>Correlated Cost Anomalies ({data.anomalies.length})</span>
          </div>
          {data.anomalies.length === 0 ? (
            <div className="text-[11px] text-slate-500 italic">No cost anomalies recorded.</div>
          ) : (
            <div className="space-y-1.5 max-h-40 overflow-y-auto">
              {data.anomalies.map((a) => (
                <div key={a.id} className="text-[11px] p-2 bg-slate-950/60 rounded border border-slate-800/80 flex items-center justify-between">
                  <div>
                    <span className="font-semibold text-slate-300">{a.title}</span>
                    <span className="ml-2 text-[10px] text-slate-500 font-mono">[{a.status}]</span>
                  </div>
                  <span className="font-mono text-rose-400">+${a.cost_impact}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
