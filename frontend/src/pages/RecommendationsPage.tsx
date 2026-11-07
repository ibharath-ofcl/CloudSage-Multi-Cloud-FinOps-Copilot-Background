import React, { useEffect, useState } from 'react';
import { useFilters } from '../context/FilterContext';
import { DashboardService } from '../services/api';
import { RecommendationSummaryResponse } from '../types/dashboard';
import { Lightbulb, Check, X, ShieldAlert, Award, Clock } from 'lucide-react';

export const RecommendationsPage: React.FC = () => {
  const { filters } = useFilters();
  const [data, setData] = useState<RecommendationSummaryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    DashboardService.getRecommendationSummary(filters)
      .then((res) => {
        if (isMounted) setData(res);
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [filters]);

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[60vh]">
        <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-900 tracking-tight">FinOps Optimization Recommendations</h1>
        <p className="text-xs text-slate-500">
          Prioritized, evidence-backed savings recommendations. Advisory-only with human review controls.
        </p>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
          <div className="text-xs font-semibold uppercase text-slate-500">Total Recommendations</div>
          <div className="text-2xl font-bold text-slate-900 font-mono mt-1">
            {data?.totalRecommendationsCount || 0}
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-indigo-200 bg-indigo-50/20 shadow-xs">
          <div className="text-xs font-semibold uppercase text-indigo-700">Open Actions</div>
          <div className="text-2xl font-bold text-indigo-700 font-mono mt-1">
            {data?.openRecommendationsCount || 0}
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-emerald-200 bg-emerald-50/20 shadow-xs">
          <div className="text-xs font-semibold uppercase text-emerald-700">Potential Monthly Savings</div>
          <div className="text-2xl font-bold text-emerald-700 font-mono mt-1">
            {data?.totalMonthlySavings || '$0.00'}
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-emerald-200 bg-emerald-50/20 shadow-xs">
          <div className="text-xs font-semibold uppercase text-emerald-700">Annualized Savings</div>
          <div className="text-2xl font-bold text-emerald-700 font-mono mt-1">
            {data?.totalAnnualSavings || '$0.00'}
          </div>
        </div>
      </div>

      {/* Recommendations Cards */}
      <div className="space-y-4">
        {data?.topRecommendations.map((r) => (
          <div
            key={r.id}
            className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs hover:border-indigo-300 transition flex flex-col md:flex-row items-start md:items-center justify-between gap-4"
          >
            <div className="space-y-2 flex-1">
              <div className="flex items-center gap-2">
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    r.priority === 'CRITICAL'
                      ? 'bg-rose-100 text-rose-800'
                      : r.priority === 'HIGH'
                      ? 'bg-amber-100 text-amber-800'
                      : 'bg-blue-100 text-blue-800'
                  }`}
                >
                  {r.priority} PRIORITY
                </span>
                <span className="text-xs font-bold text-slate-700 uppercase">{r.provider}</span>
                <span className="text-xs text-slate-400">•</span>
                <span className="text-xs font-medium text-slate-500">{r.category}</span>
                <span className="text-xs text-slate-400">•</span>
                <span className="text-xs font-medium text-slate-500">Effort: {r.effort}</span>
              </div>

              <div className="text-sm font-semibold text-slate-900">{r.action}</div>
            </div>

            <div className="flex items-center gap-6 shrink-0 w-full md:w-auto justify-between md:justify-end border-t md:border-t-0 pt-3 md:pt-0 border-slate-100">
              <div className="text-right">
                <div className="text-xs text-slate-500">Est. Savings</div>
                <div className="text-base font-bold text-emerald-600 font-mono">
                  {r.estimatedMonthlySavings}/mo
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-700 transition"
                  title="Mark as Approved"
                >
                  Approve
                </button>
                <button
                  className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-100 text-slate-700 hover:bg-slate-200 transition"
                  title="Dismiss Recommendation"
                >
                  Dismiss
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
