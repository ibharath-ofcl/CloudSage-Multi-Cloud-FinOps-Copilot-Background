import React from 'react';
import { DailySpendPoint, ProviderBreakdownItem, ServiceSpendItem } from '../types/dashboard';

interface TrendChartProps {
  data: DailySpendPoint[];
}

export const SpendTrendChart: React.FC<TrendChartProps> = ({ data }) => {
  if (!data || data.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-slate-400 text-xs">
        No spending data points available for selected range.
      </div>
    );
  }

  const maxSpend = Math.max(...data.map((d) => d.total), 1);

  return (
    <div className="h-64 flex flex-col justify-end pt-4">
      <div className="flex-1 flex items-end gap-1.5 px-2 pb-2">
        {data.slice(-20).map((pt, idx) => {
          const heightPct = Math.max(5, (pt.total / maxSpend) * 100);
          const awsPct = pt.total > 0 ? (pt.aws / pt.total) * 100 : 0;
          const azurePct = pt.total > 0 ? (pt.azure / pt.total) * 100 : 0;
          const gcpPct = pt.total > 0 ? (pt.gcp / pt.total) * 100 : 0;

          return (
            <div
              key={idx}
              className="flex-1 flex flex-col justify-end items-center group relative h-full"
            >
              {/* Tooltip */}
              <div className="opacity-0 group-hover:opacity-100 transition absolute bottom-full mb-2 bg-slate-900 text-white text-[10px] p-2 rounded shadow-lg pointer-events-none z-20 whitespace-nowrap">
                <div className="font-bold">{pt.date}</div>
                <div>Total: ${pt.total.toFixed(2)}</div>
                <div className="text-amber-300">AWS: ${pt.aws.toFixed(2)}</div>
                <div className="text-blue-300">Azure: ${pt.azure.toFixed(2)}</div>
                <div className="text-emerald-300">GCP: ${pt.gcp.toFixed(2)}</div>
              </div>

              {/* Stacked bar */}
              <div
                style={{ height: `${heightPct}%` }}
                className="w-full max-w-[28px] rounded-t overflow-hidden flex flex-col justify-end bg-slate-100"
              >
                {gcpPct > 0 && (
                  <div style={{ height: `${gcpPct}%` }} className="bg-emerald-500 w-full" />
                )}
                {azurePct > 0 && (
                  <div style={{ height: `${azurePct}%` }} className="bg-blue-500 w-full" />
                )}
                {awsPct > 0 && (
                  <div style={{ height: `${awsPct}%` }} className="bg-amber-500 w-full" />
                )}
              </div>

              <div className="text-[9px] text-slate-400 mt-1 truncate max-w-full">
                {pt.date.slice(5)}
              </div>
            </div>
          );
        })}
      </div>

      <div className="flex items-center justify-center gap-4 pt-3 border-t border-slate-100 text-[11px] text-slate-500 font-medium">
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-sm bg-amber-500"></span> AWS
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-sm bg-blue-500"></span> Azure
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-sm bg-emerald-500"></span> GCP
        </span>
      </div>
    </div>
  );
};

interface ProviderBreakdownProps {
  providers: ProviderBreakdownItem[];
}

export const ProviderBreakdownChart: React.FC<ProviderBreakdownProps> = ({ providers }) => {
  const getProviderColor = (p: string) => {
    switch (p.toUpperCase()) {
      case 'AWS':
        return 'bg-amber-500';
      case 'AZURE':
        return 'bg-blue-500';
      case 'GCP':
        return 'bg-emerald-500';
      default:
        return 'bg-purple-500';
    }
  };

  return (
    <div className="space-y-4">
      {/* Visual Multi-Segment Bar */}
      <div className="h-4 rounded-full overflow-hidden flex bg-slate-100">
        {providers.map((p) => (
          <div
            key={p.provider}
            style={{ width: `${p.percentage}%` }}
            className={`${getProviderColor(p.provider)} h-full transition-all`}
            title={`${p.provider}: ${p.percentage}%`}
          />
        ))}
      </div>

      {/* Provider Details List */}
      <div className="space-y-2.5">
        {providers.map((p) => (
          <div
            key={p.provider}
            className="flex items-center justify-between p-2.5 rounded-lg bg-slate-50 border border-slate-100 text-xs"
          >
            <div className="flex items-center gap-2">
              <span className={`w-3 h-3 rounded-full ${getProviderColor(p.provider)}`} />
              <span className="font-bold text-slate-800">{p.provider}</span>
              <span className="text-[10px] text-slate-400">({p.resourceCount} resources)</span>
            </div>
            <div className="text-right">
              <div className="font-mono font-bold text-slate-900">{p.spend}</div>
              <div className="text-[10px] text-slate-500">{p.percentage.toFixed(1)}% of total</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

interface ServiceListProps {
  services: ServiceSpendItem[];
}

export const ServiceBreakdownList: React.FC<ServiceListProps> = ({ services }) => {
  return (
    <div className="space-y-2">
      {services.slice(0, 7).map((s, idx) => (
        <div key={idx} className="space-y-1">
          <div className="flex justify-between text-xs">
            <span className="font-medium text-slate-700 truncate max-w-[200px]">
              {s.service}{' '}
              <span className="text-[10px] text-slate-400 uppercase font-mono">({s.provider})</span>
            </span>
            <span className="font-mono font-bold text-slate-900">{s.spend}</span>
          </div>
          <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
            <div
              style={{ width: `${s.percentage}%` }}
              className="h-full bg-indigo-600 rounded-full"
            />
          </div>
        </div>
      ))}
    </div>
  );
};
