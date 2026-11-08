import React, { useEffect, useState } from 'react';
import { useFilters } from '../context/FilterContext';
import { DashboardService } from '../services/api';
import { WasteSummaryResponse } from '../types/dashboard';
import { Trash2, AlertCircle, CheckCircle, ExternalLink } from 'lucide-react';

export const WastePage: React.FC = () => {
  const { filters } = useFilters();
  const [data, setData] = useState<WasteSummaryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    DashboardService.getWasteSummary(filters)
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
        <div className="w-8 h-8 border-4 border-amber-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-900 tracking-tight">Cloud Infrastructure Waste Detection</h1>
        <p className="text-xs text-slate-500">
          Continuous detection of unattached storage, idle instances, orphaned snapshots, and oversized workloads.
        </p>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
          <div className="text-xs font-semibold uppercase text-slate-500">Total Findings</div>
          <div className="text-2xl font-bold text-slate-900 font-mono mt-1">
            {data?.totalFindingsCount || 0}
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-amber-200 bg-amber-50/20 shadow-xs">
          <div className="text-xs font-semibold uppercase text-amber-700">Open Waste Findings</div>
          <div className="text-2xl font-bold text-amber-800 font-mono mt-1">
            {data?.openFindingsCount || 0}
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
          <div className="text-xs font-semibold uppercase text-slate-500">Monthly Run-Rate Waste</div>
          <div className="text-2xl font-bold text-slate-900 font-mono mt-1">
            {data?.totalMonthlyWaste || '$0.00'}
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
          <div className="text-xs font-semibold uppercase text-slate-500">Annualized Waste</div>
          <div className="text-2xl font-bold text-slate-900 font-mono mt-1">
            {data?.totalAnnualWaste || '$0.00'}
          </div>
        </div>
      </div>

      {/* Waste Findings Table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-xs">
        <div className="p-4 border-b border-slate-200 flex items-center justify-between">
          <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <Trash2 className="w-4 h-4 text-amber-600" />
            Detected Infrastructure Waste Findings
          </h2>
          <span className="text-xs text-slate-500">
            Showing {data?.topFindings.length || 0} findings
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500 uppercase text-[10px] border-b border-slate-200">
              <tr>
                <th className="p-3">Provider</th>
                <th className="p-3">Resource Identifier</th>
                <th className="p-3">Waste Category</th>
                <th className="p-3">Severity</th>
                <th className="p-3">Est. Monthly Waste</th>
                <th className="p-3">Owner / Cost Center</th>
                <th className="p-3">Status</th>
                <th className="p-3">Remediation Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data?.topFindings.map((w) => (
                <tr key={w.id} className="hover:bg-slate-50 transition">
                  <td className="p-3 font-bold text-slate-800">{w.provider}</td>
                  <td className="p-3 font-mono text-slate-700 truncate max-w-xs">{w.resourceId}</td>
                  <td className="p-3 font-medium text-slate-900">{w.wasteType}</td>
                  <td className="p-3">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                        w.severity === 'HIGH'
                          ? 'bg-amber-100 text-amber-800'
                          : 'bg-blue-100 text-blue-800'
                      }`}
                    >
                      {w.severity}
                    </span>
                  </td>
                  <td className="p-3 font-mono font-bold text-amber-700">
                    {w.estimatedMonthlyWaste}/mo
                  </td>
                  <td className="p-3 text-slate-500">{w.owner || 'Unassigned'}</td>
                  <td className="p-3">
                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-700">
                      {w.status}
                    </span>
                  </td>
                  <td className="p-3 text-slate-600 max-w-xs truncate" title={w.recommendationSnippet}>
                    {w.recommendationSnippet}
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
