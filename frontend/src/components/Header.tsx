import React from 'react';
import { useFilters } from '../context/FilterContext';
import { RefreshCw, Download, Sparkles, Filter } from 'lucide-react';
import { DashboardService } from '../services/api';

interface HeaderProps {
  onRefresh: () => void;
  onToggleCopilot: () => void;
  isLoading?: boolean;
}

export const Header: React.FC<HeaderProps> = ({ onRefresh, onToggleCopilot, isLoading }) => {
  const { filters, updateFilter, resetFilters } = useFilters();

  const handleExport = (format: 'CSV' | 'JSON') => {
    const url = DashboardService.getExportUrl(format, 'overview', filters);
    window.open(url, '_blank');
  };

  return (
    <header className="bg-white border-b border-slate-200 px-6 py-3.5 sticky top-0 z-30 flex flex-wrap items-center justify-between gap-4 shadow-xs">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <span className="text-xl font-bold tracking-tight bg-gradient-to-r from-blue-700 via-indigo-700 to-purple-800 bg-clip-text text-transparent">
            CloudSage
          </span>
          <span className="px-2 py-0.5 text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200 rounded-full">
            FinOps Command Center
          </span>
        </div>
      </div>

      {/* Global Filter Bar */}
      <div className="flex items-center gap-2.5 flex-wrap">
        <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1 text-xs">
          <Filter className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-slate-500 font-medium">Provider:</span>
          <select
            value={filters.provider || 'ALL'}
            onChange={(e) => updateFilter('provider', e.target.value)}
            className="bg-transparent font-semibold text-slate-800 focus:outline-none cursor-pointer"
          >
            <option value="ALL">All Clouds (Multi-Cloud)</option>
            <option value="AWS">Amazon Web Services</option>
            <option value="AZURE">Microsoft Azure</option>
            <option value="GCP">Google Cloud Platform</option>
          </select>
        </div>

        <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1 text-xs">
          <span className="text-slate-500 font-medium">Environment:</span>
          <select
            value={filters.environment || ''}
            onChange={(e) => updateFilter('environment', e.target.value)}
            className="bg-transparent font-semibold text-slate-800 focus:outline-none cursor-pointer"
          >
            <option value="">All Environments</option>
            <option value="production">Production</option>
            <option value="staging">Staging</option>
            <option value="development">Development</option>
          </select>
        </div>

        <button
          onClick={resetFilters}
          className="text-xs text-slate-500 hover:text-slate-800 underline px-1 cursor-pointer"
        >
          Reset
        </button>
      </div>

      {/* Action Buttons */}
      <div className="flex items-center gap-2">
        <button
          onClick={onRefresh}
          disabled={isLoading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition shadow-xs disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh
        </button>

        <div className="relative group">
          <button className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition shadow-xs">
            <Download className="w-3.5 h-3.5 text-slate-500" />
            Export
          </button>
          <div className="absolute right-0 mt-1 hidden group-hover:block bg-white border border-slate-200 rounded-lg shadow-lg py-1 w-32 z-50">
            <button
              onClick={() => handleExport('CSV')}
              className="w-full text-left px-3 py-1.5 text-xs text-slate-700 hover:bg-slate-50"
            >
              Export as CSV
            </button>
            <button
              onClick={() => handleExport('JSON')}
              className="w-full text-left px-3 py-1.5 text-xs text-slate-700 hover:bg-slate-50"
            >
              Export as JSON
            </button>
          </div>
        </div>

        <button
          onClick={onToggleCopilot}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 rounded-lg hover:opacity-95 transition shadow-sm"
        >
          <Sparkles className="w-3.5 h-3.5" />
          FinOps Copilot
        </button>
      </div>
    </header>
  );
};
