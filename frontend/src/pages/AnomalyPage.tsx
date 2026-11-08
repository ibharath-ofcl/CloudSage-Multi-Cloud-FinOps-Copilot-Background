import React, { useEffect, useState } from 'react';
import { useFilters } from '../context/FilterContext';
import { DashboardService } from '../services/api';
import { AnomalySummaryResponse } from '../types/dashboard';
import { AlertTriangle, ShieldAlert, ArrowUpRight, CheckCircle2 } from 'lucide-react';

export const AnomalyPage: React.FC = () => {
  const { filters } = useFilters();
  const [data, setData] = useState<AnomalySummaryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    DashboardService.getAnomalySummary(filters)
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
        <div className="w-8 h-8 border-4 border-rose-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-900 tracking-tight">Cost Anomaly Detection Center</h1>
        <p className="text-xs text-slate-500">
          Statistical spike detection, deviation scoring, and financial impact quantification across all providers.
        </p>
      </div>

      {/* Anomaly Metrics Overview */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
          <div className="text-xs font-semibold uppercase text-slate-500">Total Anomalies</div>
          <div className="text-2xl font-bold text-slate-900 font-mono mt-1">
            {data?.totalAnomaliesCount || 0}
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-rose-200 bg-rose-50/20 shadow-xs">
          <div className="text-xs font-semibold uppercase text-rose-700">Active Anomalies</div>
          <div className="text-2xl font-bold text-rose-700 font-mono mt-1">
            {data?.activeAnomaliesCount || 0}
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
          <div className="text-xs font-semibold uppercase text-slate-500">Total Spike Impact</div>
          <div className="text-2xl font-bold text-slate-900 font-mono mt-1">
            {data?.totalFinancialImpact || '$0.00'}
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-emerald-200 bg-emerald-50/20 shadow-xs">
          <div className="text-xs font-semibold uppercase text-emerald-700">Resolved Incidents</div>
          <div className="text-2xl font-bold text-emerald-700 font-mono mt-1">
            {data?.resolvedAnomaliesCount || 0}
          </div>
        </div>
      </div>

      {/* Anomalies Table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-xs">
        <div className="p-4 border-b border-slate-200 flex items-center justify-between">
          <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-600" />
            Detected Cost Anomalies
          </h2>
          <span className="text-xs text-slate-500">
            Showing {data?.recentAnomalies.length || 0} records
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500 uppercase text-[10px] border-b border-slate-200">
              <tr>
                <th className="p-3">Detected Date</th>
                <th className="p-3">Provider</th>
                <th className="p-3">Service</th>
                <th className="p-3">Severity</th>
                <th className="p-3">Detected Cost</th>
                <th className="p-3">Expected Baseline</th>
                <th className="p-3">Deviation Score</th>
                <th className="p-3">Status</th>
                <th className="p-3">Explanation</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data?.recentAnomalies.map((a) => (
                <tr key={a.id} className="hover:bg-slate-50 transition">
                  <td className="p-3 font-mono text-slate-600">{a.detectedDate}</td>
                  <td className="p-3 font-bold text-slate-800">{a.provider}</td>
                  <td className="p-3 font-medium text-slate-900">{a.service}</td>
                  <td className="p-3">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                        a.severity === 'CRITICAL'
                          ? 'bg-rose-100 text-rose-800'
                          : a.severity === 'HIGH'
                          ? 'bg-amber-100 text-amber-800'
                          : 'bg-blue-100 text-blue-800'
                      }`}
                    >
                      {a.severity}
                    </span>
                  </td>
                  <td className="p-3 font-mono font-bold text-rose-600">{a.detectedCost}</td>
                  <td className="p-3 font-mono text-slate-500">{a.expectedCost}</td>
                  <td className="p-3 font-mono text-slate-700">+{a.deviationScore.toFixed(2)}x</td>
                  <td className="p-3">
                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-700">
                      {a.status}
                    </span>
                  </td>
                  <td className="p-3 text-slate-600 max-w-xs truncate" title={a.explanation}>
                    {a.explanation}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
