import React, { useEffect, useState } from 'react';
import { useFilters } from '../context/FilterContext';
import { DashboardService } from '../services/api';
import { CostTrendResponse, ServiceBreakdownResponse, ProviderComparisonResponse } from '../types/dashboard';
import { SpendTrendChart, ProviderBreakdownChart, ServiceBreakdownList } from '../components/Charts';
import { BarChart2, Layers, Calendar, Cloud } from 'lucide-react';

export const CostAnalyticsPage: React.FC = () => {
  const { filters } = useFilters();
  const [granularity, setGranularity] = useState<'DAILY' | 'MONTHLY'>('DAILY');
  const [trends, setTrends] = useState<CostTrendResponse | null>(null);
  const [providers, setProviders] = useState<ProviderComparisonResponse | null>(null);
  const [services, setServices] = useState<ServiceBreakdownResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);

    Promise.all([
      DashboardService.getCostTrends(filters, granularity),
      DashboardService.getProviderComparison(filters),
      DashboardService.getServiceBreakdown(filters),
    ])
      .then(([tRes, pRes, sRes]) => {
        if (isMounted) {
          setTrends(tRes);
          setProviders(pRes);
          setServices(sRes);
        }
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [filters, granularity]);

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[60vh]">
        <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Cloud Cost Analytics & Trends</h1>
          <p className="text-xs text-slate-500">
            Multi-cloud normalized expenditure patterns, cross-provider comparisons, and service drilldowns.
          </p>
        </div>

        <div className="flex items-center gap-2 bg-slate-100 p-1 rounded-lg text-xs font-semibold">
          <button
            onClick={() => setGranularity('DAILY')}
            className={`px-3 py-1 rounded-md transition ${
              granularity === 'DAILY' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-500 hover:text-slate-900'
            }`}
          >
            Daily Spend
          </button>
          <button
            onClick={() => setGranularity('MONTHLY')}
            className={`px-3 py-1 rounded-md transition ${
              granularity === 'MONTHLY' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-500 hover:text-slate-900'
            }`}
          >
            Monthly Aggregate
          </button>
        </div>
      </div>

      {/* Main Trends Visualizer */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <BarChart2 className="w-4 h-4 text-indigo-600" />
            <h2 className="text-sm font-bold text-slate-900">
              Normalized Expenditure Over Time ({granularity})
            </h2>
          </div>
          <div className="text-xs font-mono font-bold text-slate-700">
            Total Window Spend: {trends?.totalSpend}
          </div>
        </div>
        {trends && <SpendTrendChart data={trends.points} />}
      </div>

      {/* Provider Comparison & Service Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs">
          <div className="flex items-center gap-2 mb-4">
            <Cloud className="w-4 h-4 text-blue-600" />
            <h2 className="text-sm font-bold text-slate-900">Provider Cost Comparison</h2>
          </div>
          {providers && <ProviderBreakdownChart providers={providers.providers} />}
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs">
          <div className="flex items-center gap-2 mb-4">
            <Layers className="w-4 h-4 text-purple-600" />
            <h2 className="text-sm font-bold text-slate-900">Service Cost Breakdown</h2>
          </div>
          {services && <ServiceBreakdownList services={services.services} />}
        </div>
      </div>
    </div>
  );
};
