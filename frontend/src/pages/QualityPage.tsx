import React, { useEffect, useState } from 'react';
import { useFilters } from '../context/FilterContext';
import { DashboardService } from '../services/api';
import { DataQualitySummaryResponse } from '../types/dashboard';
import { ShieldCheck, CheckCircle2, AlertTriangle, FileCheck, Layers } from 'lucide-react';

export const QualityPage: React.FC = () => {
  const { filters } = useFilters();
  const [data, setData] = useState<DataQualitySummaryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    DashboardService.getDataQualitySummary(filters)
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
        <h1 className="text-xl font-bold text-slate-900 tracking-tight">Data Quality & FOCUS 1.0 Governance</h1>
        <p className="text-xs text-slate-500">
          Validation metrics, schema standardization compliance, and tag completeness scores.
        </p>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
          <div className="text-xs font-semibold uppercase text-slate-500">Overall Quality Score</div>
          <div className="text-3xl font-bold text-slate-900 font-mono mt-1">
            {data?.overallQualityScore || 0}%
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-emerald-200 bg-emerald-50/20 shadow-xs">
          <div className="text-xs font-semibold uppercase text-emerald-700">FOCUS 1.0 Compliance</div>
          <div className="text-3xl font-bold text-emerald-700 font-mono mt-1">
            {data?.focusComplianceScore || 0}%
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
          <div className="text-xs font-semibold uppercase text-slate-500">Tagging Completeness</div>
          <div className="text-3xl font-bold text-indigo-600 font-mono mt-1">
            {data?.tagCoverageScore || 0}%
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
          <div className="text-xs font-semibold uppercase text-slate-500">Validation Warnings</div>
          <div className="text-3xl font-bold text-slate-700 font-mono mt-1">
            {data?.validationWarnings || 0}
          </div>
        </div>
      </div>

      {/* Compliance Standards Card */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-4">
        <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
          <FileCheck className="w-4 h-4 text-emerald-600" />
          FinOps Open Cost & Usage Specification (FOCUS) 1.0 Checklist
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
          <div className="flex items-center gap-2 p-3 bg-emerald-50/50 border border-emerald-100 rounded-lg text-emerald-900">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>Mandatory FOCUS dimensions validated (ProviderName, BilledCost, EffectiveCost)</span>
          </div>
          <div className="flex items-center gap-2 p-3 bg-emerald-50/50 border border-emerald-100 rounded-lg text-emerald-900">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>Strict Zero Float Rule enforced (Decimal financial arithmetic)</span>
          </div>
          <div className="flex items-center gap-2 p-3 bg-emerald-50/50 border border-emerald-100 rounded-lg text-emerald-900">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>SHA-256 idempotency & deduplication active</span>
          </div>
          <div className="flex items-center gap-2 p-3 bg-emerald-50/50 border border-emerald-100 rounded-lg text-emerald-900">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>Anti-double-counting separation across waste, anomalies, and recommendations</span>
          </div>
        </div>
      </div>
    </div>
  );
};
