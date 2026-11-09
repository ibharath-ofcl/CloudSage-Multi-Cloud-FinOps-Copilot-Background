import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  BarChart3,
  AlertTriangle,
  Trash2,
  Lightbulb,
  PiggyBank,
  Boxes,
  ShieldCheck,
  ExternalLink,
  ShieldAlert,
  Sliders,
  Bell,
  Send,
  FileSearch,
  Users,
  Key,
  Lock,
} from 'lucide-react';

export const Sidebar: React.FC = () => {
  const navItems = [
    { label: 'Executive Overview', path: '/', icon: LayoutDashboard },
    { label: 'Cost Analytics & Trends', path: '/costs', icon: BarChart3 },
    { label: 'Cost Anomalies', path: '/anomalies', icon: AlertTriangle },
    { label: 'Investigation Workspace', path: '/investigations', icon: FileSearch },
    { label: 'Alerts & Triage Hub', path: '/alerts', icon: ShieldAlert },
    { label: 'Alert Rules Governance', path: '/alert-rules', icon: Sliders },
    { label: 'Notification Center', path: '/notifications', icon: Bell },
    { label: 'Delivery Pipeline', path: '/notification-deliveries', icon: Send },
    { label: 'Infrastructure Waste', path: '/waste', icon: Trash2 },
    { label: 'Recommendations', path: '/recommendations', icon: Lightbulb },
    { label: 'Savings & Impact', path: '/savings', icon: PiggyBank },
    { label: 'Resource Inventory', path: '/inventory', icon: Boxes },
    { label: 'Ingestion & Quality', path: '/quality', icon: ShieldCheck },
  ];

  const adminNavItems = [
    { label: 'User Governance', path: '/admin/users', icon: Users },
    { label: 'Roles & Permissions', path: '/admin/roles', icon: Key },
    { label: 'Security & Audit Hub', path: '/admin/security', icon: Lock },
  ];

  return (
    <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col shrink-0 min-h-screen border-r border-slate-800">
      <div className="p-5 border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white font-black text-base shadow-inner">
            CS
          </div>
          <div>
            <div className="text-sm font-bold text-white tracking-wide">CloudSage FinOps</div>
            <div className="text-[10px] text-slate-400">Enterprise Edition v0.14.0</div>
          </div>
        </div>
      </div>

      <nav className="p-3 flex-1 space-y-4 overflow-y-auto">
        <div>
          <div className="px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-500">
            Navigation
          </div>
          <div className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition ${
                      isActive
                        ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                    }`
                  }
                >
                  <Icon className="w-4 h-4 shrink-0" />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
          </div>
        </div>

        <div>
          <div className="px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-500">
            Enterprise RBAC & Security
          </div>
          <div className="space-y-1">
            {adminNavItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition ${
                      isActive
                        ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                    }`
                  }
                >
                  <Icon className="w-4 h-4 shrink-0" />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
          </div>
        </div>
      </nav>

      <div className="p-4 border-t border-slate-800/80 space-y-2">
        <div className="p-3 bg-slate-800/50 rounded-lg border border-slate-700/50">
          <div className="text-[11px] font-semibold text-slate-200 flex items-center justify-between">
            <span>FOCUS 1.0 Aligned</span>
            <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
          </div>
          <div className="text-[10px] text-slate-400 mt-1">
            Zero Float Rule • Advisory-Only
          </div>
        </div>

        <a
          href="/docs"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-between px-3 py-2 text-xs text-slate-400 hover:text-slate-200 rounded-lg hover:bg-slate-800/60 transition"
        >
          <span>API Documentation</span>
          <ExternalLink className="w-3.5 h-3.5" />
        </a>
      </div>
    </aside>
  );
};
