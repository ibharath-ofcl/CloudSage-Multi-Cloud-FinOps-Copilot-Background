import React, { useState, useEffect } from 'react';
import { ResourceTelemetryData, MetricDataPoint } from '../types/workspace';
import { WorkspaceService } from '../services/api';

interface TelemetryPanelProps {
  resourceId?: string | null;
  recommendationId?: string;
  wasteFindingId?: string;
}

export const TelemetryPanel: React.FC<TelemetryPanelProps> = ({
  resourceId,
  recommendationId,
  wasteFindingId,
}) => {
  const [telemetry, setTelemetry] = useState<ResourceTelemetryData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedMetric, setSelectedMetric] = useState<string>('cpu_utilization_pct');
  const [days, setDays] = useState<number>(14);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);

    const fetchTelemetry = async () => {
      try {
        let data: ResourceTelemetryData;
        if (recommendationId) {
          data = await WorkspaceService.getRecommendationTelemetry(recommendationId, days);
        } else if (wasteFindingId) {
          data = await WorkspaceService.getFindingTelemetry(wasteFindingId, days);
        } else if (resourceId) {
          data = await WorkspaceService.getResourceTelemetry(resourceId, days);
        } else {
          setLoading(false);
          return;
        }

        if (isMounted) {
          setTelemetry(data);
          const metricKeys = Object.keys(data.metrics || {});
          if (metricKeys.length > 0 && !metricKeys.includes(selectedMetric)) {
            setSelectedMetric(metricKeys[0]);
          }
        }
      } catch (err) {
        console.error('Failed to load telemetry', err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchTelemetry();
    return () => {
      isMounted = false;
    };
  }, [resourceId, recommendationId, wasteFindingId, days]);

  if (loading) {
    return (
      <div className="bg-slate-800/60 rounded-xl p-6 border border-slate-700/60 flex items-center justify-center min-h-[220px]">
        <div className="flex items-center space-x-3 text-slate-400">
          <div className="w-5 h-5 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin"></div>
          <span>Loading resource telemetry...</span>
        </div>
      </div>
    );
  }

  if (!telemetry || !telemetry.has_telemetry) {
    return (
      <div className="bg-slate-800/60 rounded-xl p-6 border border-slate-700/60">
        <div className="flex items-start space-x-3">
          <div className="p-2 bg-amber-500/10 text-amber-400 rounded-lg shrink-0">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div>
            <h4 className="text-sm font-semibold text-slate-200">No Telemetry Recorded</h4>
            <p className="text-xs text-slate-400 mt-1">
              {telemetry?.message || 'No telemetry metric observations were recorded for this resource.'}
            </p>
            <div className="mt-3 text-xs text-slate-500 bg-slate-900/60 rounded p-2.5 border border-slate-800 font-mono">
              Note: CloudSage strictly adheres to FinOps telemetry truthfulness and never fabricates mock metrics in production analysis.
            </div>
          </div>
        </div>
      </div>
    );
  }

  const metricNames = Object.keys(telemetry.metrics);
  const activePoints: MetricDataPoint[] = telemetry.metrics[selectedMetric] || [];
  const activeSummary = telemetry.summary[selectedMetric];

  // SVG Chart Calculation
  const maxVal = Math.max(...activePoints.map((p) => Math.max(p.average, p.peak)), 10);
  const chartHeight = 140;
  const chartWidth = 560;

  const pointsSvg = activePoints
    .map((p, idx) => {
      const x = (idx / Math.max(activePoints.length - 1, 1)) * chartWidth;
      const y = chartHeight - (p.average / maxVal) * (chartHeight - 20) - 10;
      return `${x},${y}`;
    })
    .join(' ');

  const peakSvg = activePoints
    .map((p, idx) => {
      const x = (idx / Math.max(activePoints.length - 1, 1)) * chartWidth;
      const y = chartHeight - (p.peak / maxVal) * (chartHeight - 20) - 10;
      return `${x},${y}`;
    })
    .join(' ');

  return (
    <div className="bg-slate-800/60 rounded-xl p-5 border border-slate-700/60">
      {/* Header & Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div>
          <h4 className="text-sm font-semibold text-slate-200">Resource Telemetry Proof</h4>
          <p className="text-xs text-slate-400">Observed metrics over past {telemetry.observation_window_days} days</p>
        </div>

        <div className="flex items-center space-x-2">
          {/* Metric Selector */}
          <select
            value={selectedMetric}
            onChange={(e) => setSelectedMetric(e.target.value)}
            className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
          >
            {metricNames.map((name) => (
              <option key={name} value={name}>
                {name.replace(/_/g, ' ')}
              </option>
            ))}
          </select>

          {/* Days Selector */}
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="bg-slate-900 border border-slate-700 rounded-lg px-2 py-1 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
          >
            <option value={7}>7d</option>
            <option value={14}>14d</option>
            <option value={30}>30d</option>
          </select>
        </div>
      </div>

      {/* Metric Summary Badges */}
      {activeSummary && (
        <div className="grid grid-cols-4 gap-2 mb-4">
          <div className="bg-slate-900/60 rounded p-2 text-center border border-slate-800">
            <div className="text-[10px] text-slate-400 uppercase font-mono">Avg</div>
            <div className="text-sm font-bold text-slate-100">{activeSummary.avg}</div>
          </div>
          <div className="bg-slate-900/60 rounded p-2 text-center border border-slate-800">
            <div className="text-[10px] text-slate-400 uppercase font-mono">Max Peak</div>
            <div className="text-sm font-bold text-amber-400">{activeSummary.max}</div>
          </div>
          <div className="bg-slate-900/60 rounded p-2 text-center border border-slate-800">
            <div className="text-[10px] text-slate-400 uppercase font-mono">Min</div>
            <div className="text-sm font-bold text-emerald-400">{activeSummary.min}</div>
          </div>
          <div className="bg-slate-900/60 rounded p-2 text-center border border-slate-800">
            <div className="text-[10px] text-slate-400 uppercase font-mono">Latest</div>
            <div className="text-sm font-bold text-indigo-400">{activeSummary.latest}</div>
          </div>
        </div>
      )}

      {/* SVG Time-Series Chart */}
      <div className="bg-slate-900/80 rounded-lg p-3 border border-slate-800 overflow-hidden">
        <div className="flex items-center justify-between text-[11px] text-slate-400 mb-2">
          <span className="font-mono text-indigo-300">● Average Value</span>
          <span className="font-mono text-amber-400">--- Peak Observation</span>
          <span>Sample Count: {activePoints.length}</span>
        </div>

        <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} className="w-full h-36">
          {/* Grid lines */}
          <line x1="0" y1="10" x2={chartWidth} y2="10" stroke="#334155" strokeDasharray="3 3" />
          <line x1="0" y1={chartHeight / 2} x2={chartWidth} y2={chartHeight / 2} stroke="#334155" strokeDasharray="3 3" />
          <line x1="0" y1={chartHeight - 10} x2={chartWidth} y2={chartHeight - 10} stroke="#334155" />

          {/* Peak line */}
          {activePoints.length > 1 && (
            <polyline
              fill="none"
              stroke="#fbbf24"
              strokeWidth="1.5"
              strokeDasharray="4 4"
              points={peakSvg}
            />
          )}

          {/* Average line */}
          {activePoints.length > 1 && (
            <polyline
              fill="none"
              stroke="#6366f1"
              strokeWidth="2.5"
              points={pointsSvg}
            />
          )}

          {/* Individual points */}
          {activePoints.map((p, idx) => {
            const x = (idx / Math.max(activePoints.length - 1, 1)) * chartWidth;
            const y = chartHeight - (p.average / maxVal) * (chartHeight - 20) - 10;
            return (
              <circle
                key={idx}
                cx={x}
                cy={y}
                r="3"
                className="fill-indigo-400 hover:fill-white cursor-pointer"
              />
            );
          })}
        </svg>
      </div>
    </div>
  );
};
