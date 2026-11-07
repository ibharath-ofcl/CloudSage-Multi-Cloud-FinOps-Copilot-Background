import React, { useEffect, useState } from 'react';
import { useFilters } from '../context/FilterContext';
import { DashboardService } from '../services/api';
import { SavingsSummaryResponse } from '../types/dashboard';
import { PiggyBank, Target, Award, ArrowUpRight, TrendingUp } from 'lucide-react';

export const SavingsPage: React.FC = () => {
  const { filters } = useFilters();
  const [data, setData] = useState<SavingsSummaryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    DashboardService.getSavingsSummary(filters)
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
        <div className="w-8 h-8 border-4 border-emerald-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-900 tracking-tight">Realized & Potential Savings</h1>
        <p className="text-xs text-slate-500">
          Financial ledger of captured cloud savings, active optimization pipeline, and realization efficiency.
        </p>
      </div>

      {/* Main KPI Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center gap-2 text-slate-500 mb-2">
            <Target className="w-4 h-4 text-blue-600" />
            <span className="text-xs font-semibold uppercase">Potential Savings</span>
          </div>
          <div className="text-3xl font-bold text-slate-900 font-mono">
            {data?.potentialMonthlySavings || '$0.00'}/mo
          </div>
          <div className="text-xs text-slate-500 mt-2">
            Annualized Pipeline: {data?.potentialAnnualSavings}
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-emerald-200 bg-emerald-50/20 shadow-xs">
          <div className="flex items-center gap-2 text-emerald-700 mb-2">
            <PiggyBank className="w-4 h-4 text-emerald-600" />
            <span className="text-xs font-semibold uppercase">Realized Savings</span>
          </div>
          <div className="text-3xl font-bold text-emerald-700 font-mono">
            {data?.realizedMonthlySavings || '$0.00'}/mo
          </div>
          <div className="text-xs text-emerald-800 mt-2">
            Annualized Verified: {data?.realizedAnnualSavings}
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-indigo-200 bg-indigo-50/20 shadow-xs">
          <div className="flex items-center gap-2 text-indigo-700 mb-2">
            <TrendingUp className="w-4 h-4 text-indigo-600" />
            <span className="text-xs font-semibold uppercase">Realization Efficiency</span>
          </div>
          <div className="text-3xl font-bold text-indigo-700 font-mono">
            {data?.realizationRatePct.toFixed(1)}%
          </div>
          <div className="text-xs text-indigo-800 mt-2">
            Proportion of pipeline successfully actioned
          </div>
        </div>
      </div>

      {/* Provider & Category Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs">
          <h2 className="text-sm font-bold text-slate-900 mb-4">Savings Pipeline by Provider</h2>
          <div className="space-y-3">
            {Object.entries(data?.savingsByProvider || {}).map(([prov, amt]) => (
              <div key={prov} className="flex justify-between items-center p-3 bg-slate-50 rounded-lg text-xs">
                <span className="font-bold text-slate-800">{prov}</span>
                <span className="font-mono font-bold text-emerald-600">{amt}/mo</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs">
          <h2 className="text-sm font-bold text-slate-900 mb-4">Savings by Optimization Category</h2>
          <div className="space-y-3">
            {Object.entries(data?.savingsByCategory || {}).map(([cat, amt]) => (
              <div key={cat} className="flex justify-between items-center p-3 bg-slate-50 rounded-lg text-xs">
                <span className="font-medium text-slate-700">{cat}</span>
                <span className="font-mono font-bold text-emerald-600">{amt}/mo</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
