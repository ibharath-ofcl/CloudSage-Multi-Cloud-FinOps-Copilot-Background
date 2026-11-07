import React from 'react';
import { ArrowUpRight, ArrowDownRight, Minus, LucideIcon } from 'lucide-react';

interface KpiCardProps {
  title: string;
  value: string;
  changePct?: number | null;
  trend?: 'UP' | 'DOWN' | 'NEUTRAL';
  subtitle?: string | null;
  isPositiveGood?: boolean;
  icon?: LucideIcon;
  badge?: string;
}

export const KpiCard: React.FC<KpiCardProps> = ({
  title,
  value,
  changePct,
  trend = 'NEUTRAL',
  subtitle,
  isPositiveGood = false,
  icon: Icon,
  badge,
}) => {
  const isUp = trend === 'UP';
  const isDown = trend === 'DOWN';

  // For cost: UP is bad (red), DOWN is good (green).
  // For savings: UP is good (green), DOWN is bad (red).
  const isGood = isPositiveGood ? isUp : isDown;
  const isBad = isPositiveGood ? isDown : isUp;

  const trendColor = isGood
    ? 'text-emerald-700 bg-emerald-50 border-emerald-200'
    : isBad
    ? 'text-rose-700 bg-rose-50 border-rose-200'
    : 'text-slate-600 bg-slate-50 border-slate-200';

  return (
    <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs hover:shadow-sm transition-all flex flex-col justify-between">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="space-y-0.5">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            {title}
          </span>
          {badge && (
            <span className="ml-2 inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-600">
              {badge}
            </span>
          )}
        </div>
        {Icon && (
          <div className="p-2 rounded-lg bg-slate-50 border border-slate-100 text-slate-500 shrink-0">
            <Icon className="w-4 h-4" />
          </div>
        )}
      </div>

      <div className="space-y-1">
        <div className="text-2xl font-bold tracking-tight text-slate-900 font-mono">
          {value}
        </div>

        <div className="flex items-center gap-2 pt-1 flex-wrap">
          {changePct !== undefined && changePct !== null && (
            <span
              className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[11px] font-semibold border ${trendColor}`}
            >
              {isUp && <ArrowUpRight className="w-3 h-3" />}
              {isDown && <ArrowDownRight className="w-3 h-3" />}
              {trend === 'NEUTRAL' && <Minus className="w-3 h-3" />}
              {Math.abs(changePct).toFixed(1)}% MoM
            </span>
          )}

          {subtitle && (
            <span className="text-xs text-slate-500 truncate">{subtitle}</span>
          )}
        </div>
      </div>
    </div>
  );
};
