import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  Shield,
  Key,
  RefreshCw,
  Users,
  CheckCircle2,
  Lock,
  Search,
} from 'lucide-react';
import { RoleAdminService } from '../services/securityApi';
import { RoleDetail, Permission } from '../types/security';

export const RoleManagementPage: React.FC = () => {
  const [roles, setRoles] = useState<RoleDetail[]>([]);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [selectedRole, setSelectedRole] = useState<RoleDetail | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [permSearch, setPermSearch] = useState('');

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [roleData, permData] = await Promise.all([
        RoleAdminService.listRoles(),
        RoleAdminService.listPermissions(),
      ]);
      setRoles(roleData);
      setPermissions(permData);
      if (roleData.length > 0 && !selectedRole) {
        setSelectedRole(roleData[0]);
      }
    } catch (err) {
      console.error('Failed to load roles/permissions', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const filteredPerms = permissions.filter(
    (p) =>
      p.name.toLowerCase().includes(permSearch.toLowerCase()) ||
      p.resource.toLowerCase().includes(permSearch.toLowerCase()) ||
      p.action.toLowerCase().includes(permSearch.toLowerCase()) ||
      (p.description && p.description.toLowerCase().includes(permSearch.toLowerCase()))
  );

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-6 h-6 text-indigo-600" />
            <h1 className="text-xl font-bold text-slate-900">
              Enterprise Role-Based Access Control (RBAC)
            </h1>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            7 canonical enterprise roles mapped to fine-grained resource-action permission taxonomy.
          </p>
        </div>

        <button
          onClick={loadData}
          disabled={isLoading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Roles List (Left Column) */}
        <div className="lg:col-span-5 space-y-3">
          <div className="text-xs font-bold text-slate-500 uppercase tracking-wider px-1">
            Configured Roles ({roles.length})
          </div>

          <div className="space-y-2">
            {roles.map((r) => {
              const isSelected = selectedRole?.id === r.id;
              return (
                <div
                  key={r.id}
                  onClick={() => setSelectedRole(r)}
                  className={`p-4 rounded-xl border transition cursor-pointer ${
                    isSelected
                      ? 'bg-indigo-50/60 border-indigo-300 shadow-xs'
                      : 'bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50/60'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-xs text-slate-900">{r.display_name}</span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 font-mono text-slate-600 font-semibold">
                          {r.name}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-500 mt-1 leading-relaxed">
                        {r.description || 'No description provided.'}
                      </p>
                    </div>

                    <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-slate-600 bg-slate-100 px-2 py-0.5 rounded-full shrink-0">
                      <Users className="w-3 h-3 text-slate-400" /> {r.user_count}
                    </span>
                  </div>

                  <div className="mt-3 flex items-center justify-between text-[11px] text-slate-500 border-t border-slate-100 pt-2">
                    <span className="flex items-center gap-1">
                      <Key className="w-3 h-3 text-indigo-500" />
                      {r.permissions.includes('*') ? (
                        <span className="font-bold text-purple-700">All Capabilities (*)</span>
                      ) : (
                        <span>{r.permissions.length} Permissions</span>
                      )}
                    </span>
                    <span className="text-[10px] text-slate-400">System Protected</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Selected Role Permissions Detail (Right Column) */}
        <div className="lg:col-span-7 space-y-4">
          {selectedRole ? (
            <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-5 space-y-5">
              <div className="flex items-start justify-between border-b border-slate-100 pb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <Shield className="w-5 h-5 text-indigo-600" />
                    <h2 className="text-base font-bold text-slate-900">
                      {selectedRole.display_name}
                    </h2>
                  </div>
                  <p className="text-xs text-slate-500 mt-1">{selectedRole.description}</p>
                </div>

                <div className="text-right">
                  <div className="text-xs font-semibold text-slate-700">
                    {selectedRole.permissions.includes('*')
                      ? 'Full Wildcard Authority'
                      : `${selectedRole.permissions.length} Active Permissions`}
                  </div>
                  <div className="text-[10px] text-slate-400">Advisory-Only Enforcement</div>
                </div>
              </div>

              {/* Permission Search */}
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  placeholder="Search role permissions by domain, resource, or action..."
                  value={permSearch}
                  onChange={(e) => setPermSearch(e.target.value)}
                  className="w-full pl-9 pr-3 py-1.5 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              {/* Permissions Grid */}
              <div className="space-y-2 max-h-[500px] overflow-y-auto pr-1">
                {filteredPerms.map((perm) => {
                  const hasPerm =
                    selectedRole.permissions.includes('*') ||
                    selectedRole.permissions.includes(perm.name);
                  return (
                    <div
                      key={perm.id}
                      className={`flex items-center justify-between p-2.5 rounded-lg border text-xs transition ${
                        hasPerm
                          ? 'bg-emerald-50/40 border-emerald-200'
                          : 'bg-slate-50/50 border-slate-100 opacity-60'
                      }`}
                    >
                      <div className="flex items-center gap-2.5">
                        {hasPerm ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                        ) : (
                          <Lock className="w-4 h-4 text-slate-300 shrink-0" />
                        )}
                        <div>
                          <div className="font-mono font-semibold text-slate-800">{perm.name}</div>
                          <div className="text-[11px] text-slate-500">
                            {perm.description || `Permits ${perm.action} on ${perm.resource}`}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-1.5">
                        <span className="px-2 py-0.5 rounded bg-white border border-slate-200 text-[10px] font-mono text-slate-600">
                          {perm.resource}
                        </span>
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            hasPerm
                              ? 'bg-emerald-100 text-emerald-800'
                              : 'bg-slate-200 text-slate-600'
                          }`}
                        >
                          {hasPerm ? 'GRANTED' : 'DENIED'}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-xl border border-slate-200 p-8 text-center text-slate-400">
              Select a role to inspect its granted permissions.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

