import React, { useEffect, useState } from 'react';
import { useFilters } from '../context/FilterContext';
import { DashboardService } from '../services/api';
import { DashboardOverviewResponse } from '../types/dashboard';
import { KpiCard } from '../components/KpiCard';
import { SpendTrendChart, ProviderBreakdownChart, ServiceBreakdownList } from '../components/Charts';
import {
  DollarSign,
  TrendingDown,
  AlertTriangle,
  Lightbulb,
  PiggyBank,
  ShieldCheck,
  CheckCircle2,
  Clock,
} from 'lucide-react';

export const OverviewPage: React.FC = () => {
  const { filters } = useFilters();
  const [data, setData] = useState<DashboardOverviewResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    DashboardService.getOverview(filters)
      .then((res) => {
        if (isMounted) {
          setData(res);
          setError(null);
        }
      })
      .catch((err) => {
        if (isMounted) setError(err.message || 'Failed to load dashboard overview');
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
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
          <span className="text-xs text-slate-500 font-medium">Loading FinOps metrics...</span>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-8">
        <div className="bg-rose-50 border border-rose-200 text-rose-800 p-4 rounded-xl text-xs">
          {error || 'Unable to load dashboard overview.'}
        </div>
      </div>
    );
  }

  const { kpis, providerBreakdown, recentSpendTrend, topServices, recentAnomalies, topWasteFindings } = data;

  return (
    <div className="p-6 space-y-6">
      {/* Page Title & Status Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Executive FinOps Command Center</h1>
          <p className="text-xs text-slate-500">
            Real-time multi-cloud financial posture across AWS, Azure, and Google Cloud Platform.
          </p>
        </div>
        <div className="flex items-center gap-2 text-[11px] text-slate-500 bg-white border border-slate-200 px-3 py-1.5 rounded-lg shadow-xs">
          <Clock className="w-3.5 h-3.5 text-slate-400" />
          <span>Updated: {new Date(data.generatedAt).toLocaleTimeString()}</span>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        <KpiCard
          title="Total Cloud Spend"
          value={kpis.totalSpend}
          changePct={kpis.momChangePct}
          trend={kpis.momChangePct > 0 ? 'UP' : kpis.momChangePct < 0 ? 'DOWN' : 'NEUTRAL'}
          subtitle={`MTD: ${kpis.monthToDateSpend}`}
          icon={DollarSign}
        />
        <KpiCard
          title="Forecasted Spend"
          value={kpis.forecastedMonthlySpend}
          subtitle="Projected End of Month"
          icon={TrendingDown}
        />
        <KpiCard
          title="Detected Waste"
          value={kpis.detectedWaste}
          subtitle={`${kpis.wastePercentageOfSpend.toFixed(1)}% of total expenditure`}
          icon={TrendingDown}
          isPositiveGood={false}
          badge="Idle/Orphaned"
        />
        <KpiCard
          title="Anomaly Impact"
          value={kpis.anomalyImpact}
          subtitle={`${kpis.activeAnomalyCount} active spike incidents`}
          icon={AlertTriangle}
          isPositiveGood={false}
        />
        <KpiCard
          title="Potential Savings"
          value={kpis.potentialSavings}
          subtitle={`${kpis.activeRecommendationsCount} recommendations`}
          icon={Lightbulb}
          isPositiveGood={true}
        />
        <KpiCard
          title="Realized Savings"
          value={kpis.realizedSavings}
          subtitle="Actioned & verified"
          icon={PiggyBank}
          isPositiveGood={true}
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Spend Trend Chart (2 columns) */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
          <div className="flex items-center justify-between mb-2">
            <div>
              <h2 className="text-sm font-bold text-slate-900">Multi-Cloud Daily Spend Trend</h2>
              <p className="text-[11px] text-slate-500">Stacked expenditure by cloud provider</p>
            </div>
            <span className="text-xs font-semibold px-2 py-0.5 bg-slate-100 rounded text-slate-700">
              Last 30 Days
            </span>
          </div>
          <SpendTrendChart data={recentSpendTrend} />
        </div>

        {/* Provider Breakdown Donut / List */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="mb-4">
              <h2 className="text-sm font-bold text-slate-900">Cloud Distribution</h2>
              <p className="text-[11px] text-slate-500">Spend allocation across providers</p>
            </div>
            <ProviderBreakdownChart providers={providerBreakdown} />
          </div>

          <div className="pt-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span>Data Quality: {kpis.dataQualityScore}%</span>
            <span>Resources: {kpis.totalTrackedResources}</span>
          </div>
        </div>
      </div>

      {/* Findings & Services Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Top Services */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
          <div className="mb-3">
            <h2 className="text-sm font-bold text-slate-900">Top Expenditure Services</h2>
            <p className="text-[11px] text-slate-500">Highest consuming cloud products</p>
          </div>
          <ServiceBreakdownList services={topServices} />
        </div>

        {/* Active Cost Anomalies */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-sm font-bold text-slate-900">Active Cost Anomalies</h2>
              <p className="text-[11px] text-slate-500">High-confidence deviation alerts</p>
            </div>
            <span className="text-xs font-bold text-rose-600 bg-rose-50 px-2 py-0.5 rounded-full border border-rose-200">
              {recentAnomalies.length} Active
            </span>
          </div>

          {recentAnomalies.length === 0 ? (
            <div className="py-8 text-center text-xs text-slate-400">
              No unresolved cost anomalies detected.
            </div>
          ) : (
            <div className="space-y-2.5">
              {recentAnomalies.slice(0, 4).map((a) => (
                <div
                  key={a.id}
                  className="p-3 rounded-lg border border-rose-100 bg-rose-50/40 text-xs space-y-1"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-rose-900 truncate">
                      {a.service} ({a.provider})
                    </span>
                    <span className="font-mono font-bold text-rose-700">+{a.detectedCost}</span>
                  </div>
                  <p className="text-[11px] text-slate-600 line-clamp-1">{a.explanation}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* High-Impact Waste Findings */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-sm font-bold text-slate-900">Infrastructure Waste Findings</h2>
              <p className="text-[11px] text-slate-500">Actionable idle & orphaned assets</p>
            </div>
            <span className="text-xs font-bold text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200">
              {topWasteFindings.length} Open
            </span>
          </div>

          {topWasteFindings.length === 0 ? (
            <div className="py-8 text-center text-xs text-slate-400">
              Zero open infrastructure waste findings!
            </div>
          ) : (
            <div className="space-y-2.5">
              {topWasteFindings.slice(0, 4).map((w) => (
                <div
                  key={w.id}
                  className="p-3 rounded-lg border border-amber-100 bg-amber-50/40 text-xs space-y-1"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-amber-900 truncate">
                      {w.wasteType} ({w.provider})
                    </span>
                    <span className="font-mono font-bold text-amber-800">
                      ~{w.estimatedMonthlyWaste}/mo
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-600 line-clamp-1">{w.recommendationSnippet}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
