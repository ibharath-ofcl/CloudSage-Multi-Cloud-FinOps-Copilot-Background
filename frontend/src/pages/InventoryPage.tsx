import React, { useEffect, useState } from 'react';
import { useFilters } from '../context/FilterContext';
import { DashboardService } from '../services/api';
import { InventorySummaryResponse } from '../types/dashboard';
import { Boxes, Cloud, CheckCircle2, AlertOctagon, Tag } from 'lucide-react';

export const InventoryPage: React.FC = () => {
  const { filters } = useFilters();
  const [data, setData] = useState<InventorySummaryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    DashboardService.getInventorySummary(filters)
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
        <h1 className="text-xl font-bold text-slate-900 tracking-tight">Multi-Cloud Resource Inventory</h1>
        <p className="text-xs text-slate-500">
          Discovered cloud assets, lifecycle status, unattached resources, and tag coverage intelligence.
        </p>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
          <div className="text-xs font-semibold uppercase text-slate-500">Tracked Resources</div>
          <div className="text-2xl font-bold text-slate-900 font-mono mt-1">
            {data?.totalResources || 0}
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
          <div className="text-xs font-semibold uppercase text-slate-500">Tagging Coverage</div>
          <div className="text-2xl font-bold text-indigo-600 font-mono mt-1">
            {data?.taggedPercentage.toFixed(1) || 0}%
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-amber-200 bg-amber-50/20 shadow-xs">
          <div className="text-xs font-semibold uppercase text-amber-700">Unattached Assets</div>
          <div className="text-2xl font-bold text-amber-800 font-mono mt-1">
            {data?.unattachedCount || 0}
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
          <div className="text-xs font-semibold uppercase text-slate-500">Sync Status</div>
          <div className="text-sm font-semibold text-emerald-700 mt-2 flex items-center gap-1.5">
            <CheckCircle2 className="w-4 h-4" /> Live Inventory Synced
          </div>
        </div>
      </div>

      {/* Breakdown by Provider and Status */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs">
          <h2 className="text-sm font-bold text-slate-900 mb-4">Inventory by Cloud Provider</h2>
          <div className="space-y-3">
            {Object.entries(data?.byProvider || {}).map(([p, cnt]) => (
              <div key={p} className="flex justify-between items-center p-3 bg-slate-50 rounded-lg text-xs">
                <span className="font-bold text-slate-800">{p}</span>
                <span className="font-mono font-bold text-slate-900">{cnt} assets</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs">
          <h2 className="text-sm font-bold text-slate-900 mb-4">Inventory by Operational Status</h2>
          <div className="space-y-3">
            {Object.entries(data?.byStatus || {}).map(([s, cnt]) => (
              <div key={s} className="flex justify-between items-center p-3 bg-slate-50 rounded-lg text-xs">
                <span className="font-medium text-slate-700 uppercase">{s}</span>
                <span className="font-mono font-bold text-slate-900">{cnt} resources</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
