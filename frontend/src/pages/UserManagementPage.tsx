import React, { useState, useEffect } from 'react';
import {
  Users,
  UserPlus,
  ShieldAlert,
  Search,
  Filter,
  RefreshCw,
  LogOut,
  Edit2,
  Lock,
  Unlock,
  CheckCircle2,
  XCircle,
} from 'lucide-react';
import { UserAdminService, SecurityAuth } from '../services/securityApi';
import { UserSummary, UserCreatePayload } from '../types/security';
import { PermissionGate } from '../components/PermissionGate';

export const UserManagementPage: React.FC = () => {
  const [users, setUsers] = useState<UserSummary[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<UserSummary | null>(null);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Form states for Create User
  const [formData, setFormData] = useState<UserCreatePayload>({
    email: '',
    full_name: '',
    password: '',
    role: 'FINOPS_ANALYST',
    department: 'Engineering',
  });

  const loadUsers = async () => {
    setIsLoading(true);
    try {
      const data = await UserAdminService.listUsers({
        search: search || undefined,
        role: roleFilter || undefined,
      });
      setUsers(data);
    } catch (err: any) {
      setMessage({
        type: 'error',
        text: err.response?.data?.detail || 'Failed to load users',
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, [roleFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadUsers();
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await UserAdminService.createUser(formData);
      setMessage({ type: 'success', text: `User ${formData.email} created successfully.` });
      setIsCreateModalOpen(false);
      setFormData({
        email: '',
        full_name: '',
        password: '',
        role: 'FINOPS_ANALYST',
        department: 'Engineering',
      });
      loadUsers();
    } catch (err: any) {
      setMessage({
        type: 'error',
        text: err.response?.data?.detail || 'Failed to create user',
      });
    }
  };

  const handleUpdateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingUser) return;
    try {
      await UserAdminService.updateUser(editingUser.id, {
        full_name: editingUser.full_name,
        role: editingUser.role,
        department: editingUser.department,
        is_active: editingUser.is_active,
        is_locked: editingUser.is_locked,
      });
      setMessage({ type: 'success', text: `User ${editingUser.email} updated successfully.` });
      setEditingUser(null);
      loadUsers();
    } catch (err: any) {
      setMessage({
        type: 'error',
        text: err.response?.data?.detail || 'Failed to update user',
      });
    }
  };

  const handleRevokeSessions = async (userId: string, email: string) => {
    if (!window.confirm(`Revoke all active sessions for ${email}?`)) return;
    try {
      const res = await UserAdminService.revokeUserSessions(userId);
      setMessage({
        type: 'success',
        text: `Revoked ${res.revoked_count} active sessions for ${email}.`,
      });
      loadUsers();
    } catch (err: any) {
      setMessage({
        type: 'error',
        text: err.response?.data?.detail || 'Failed to revoke sessions',
      });
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Users className="w-6 h-6 text-blue-600" />
            <h1 className="text-xl font-bold text-slate-900">User Administration & Governance</h1>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Provision users, assign enterprise RBAC roles, audit failed logins, and revoke sessions.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={loadUsers}
            disabled={isLoading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </button>

          <PermissionGate permission="user:create">
            <button
              onClick={() => setIsCreateModalOpen(true)}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition shadow-xs"
            >
              <UserPlus className="w-3.5 h-3.5" />
              Add User
            </button>
          </PermissionGate>
        </div>
      </div>

      {/* Alert banner */}
      {message && (
        <div
          className={`p-3 rounded-lg text-xs font-medium flex items-center justify-between ${
            message.type === 'success'
              ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
              : 'bg-rose-50 text-rose-800 border border-rose-200'
          }`}
        >
          <span>{message.text}</span>
          <button onClick={() => setMessage(null)} className="font-bold underline ml-2">
            Dismiss
          </button>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-wrap items-center justify-between gap-3">
        <form onSubmit={handleSearchSubmit} className="flex items-center gap-2 flex-1 max-w-md">
          <div className="relative w-full">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search by name, email, or department..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <button
            type="submit"
            className="px-3 py-1.5 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition"
          >
            Filter
          </button>
        </form>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-500">Role:</span>
            <select
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
              className="border border-slate-200 rounded-lg px-2 py-1 text-xs bg-white text-slate-700 focus:outline-none"
            >
              <option value="">All Enterprise Roles</option>
              <option value="SUPER_ADMIN">SUPER_ADMIN</option>
              <option value="ORGANIZATION_ADMIN">ORGANIZATION_ADMIN</option>
              <option value="FINOPS_MANAGER">FINOPS_MANAGER</option>
              <option value="FINOPS_ANALYST">FINOPS_ANALYST</option>
              <option value="CLOUD_ENGINEER">CLOUD_ENGINEER</option>
              <option value="SECURITY_AUDITOR">SECURITY_AUDITOR</option>
              <option value="VIEWER">VIEWER</option>
            </select>
          </div>
        </div>
      </div>

      {/* Users Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider">
              <th className="py-3 px-4">User</th>
              <th className="py-3 px-4">Role</th>
              <th className="py-3 px-4">Department</th>
              <th className="py-3 px-4">Status</th>
              <th className="py-3 px-4">Failed Logins</th>
              <th className="py-3 px-4">Last Login</th>
              <th className="py-3 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {users.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-8 text-center text-slate-400">
                  {isLoading ? 'Loading users...' : 'No users match criteria.'}
                </td>
              </tr>
            ) : (
              users.map((u) => (
                <tr key={u.id} className="hover:bg-slate-50/80 transition">
                  <td className="py-3 px-4">
                    <div className="font-semibold text-slate-900">{u.full_name}</div>
                    <div className="text-[11px] text-slate-500">{u.email}</div>
                  </td>
                  <td className="py-3 px-4">
                    <span
                      className={`inline-flex px-2 py-0.5 rounded-full text-[10px] font-semibold tracking-wide ${
                        u.role === 'SUPER_ADMIN'
                          ? 'bg-purple-100 text-purple-800 border border-purple-200'
                          : u.role === 'ORGANIZATION_ADMIN'
                          ? 'bg-blue-100 text-blue-800 border border-blue-200'
                          : u.role === 'FINOPS_MANAGER'
                          ? 'bg-indigo-100 text-indigo-800 border border-indigo-200'
                          : u.role === 'SECURITY_AUDITOR'
                          ? 'bg-amber-100 text-amber-800 border border-amber-200'
                          : 'bg-slate-100 text-slate-700'
                      }`}
                    >
                      {u.role}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-slate-600">{u.department || '—'}</td>
                  <td className="py-3 px-4">
                    {u.is_locked ? (
                      <span className="inline-flex items-center gap-1 text-rose-700 font-semibold bg-rose-50 px-2 py-0.5 rounded-md border border-rose-200">
                        <Lock className="w-3 h-3" /> Locked
                      </span>
                    ) : u.is_active ? (
                      <span className="inline-flex items-center gap-1 text-emerald-700 font-medium bg-emerald-50 px-2 py-0.5 rounded-md">
                        <CheckCircle2 className="w-3 h-3" /> Active
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-slate-500 bg-slate-100 px-2 py-0.5 rounded-md">
                        <XCircle className="w-3 h-3" /> Deactivated
                      </span>
                    )}
                  </td>
                  <td className="py-3 px-4">
                    <span
                      className={
                        u.failed_login_attempts > 0 ? 'text-amber-600 font-bold' : 'text-slate-400'
                      }
                    >
                      {u.failed_login_attempts}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-slate-500">
                    {u.last_login_at ? new Date(u.last_login_at).toLocaleString() : 'Never'}
                  </td>
                  <td className="py-3 px-4 text-right space-x-2">
                    <PermissionGate permission="user:update">
                      <button
                        onClick={() => setEditingUser(u)}
                        className="inline-flex items-center gap-1 text-slate-600 hover:text-blue-600 font-medium px-2 py-1 rounded bg-slate-100 hover:bg-slate-200 transition"
                      >
                        <Edit2 className="w-3 h-3" /> Edit
                      </button>
                    </PermissionGate>

                    <PermissionGate permission="user:revoke_session">
                      <button
                        onClick={() => handleRevokeSessions(u.id, u.email)}
                        className="inline-flex items-center gap-1 text-slate-600 hover:text-rose-600 font-medium px-2 py-1 rounded bg-slate-100 hover:bg-rose-50 transition"
                        title="Revoke all active sessions"
                      >
                        <LogOut className="w-3 h-3" /> Revoke
                      </button>
                    </PermissionGate>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Create User Modal */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200">
            <h2 className="text-base font-bold text-slate-900 mb-4">Provision Enterprise User</h2>
            <form onSubmit={handleCreateSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Full Name</label>
                <input
                  type="text"
                  required
                  value={formData.full_name}
                  onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 focus:ring-1 focus:ring-blue-500 outline-none"
                  placeholder="e.g. Alice Smith"
                />
              </div>

              <div>
                <label className="block text-slate-700 font-semibold mb-1">Email Address</label>
                <input
                  type="email"
                  required
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 focus:ring-1 focus:ring-blue-500 outline-none"
                  placeholder="e.g. alice@enterprise.com"
                />
              </div>

              <div>
                <label className="block text-slate-700 font-semibold mb-1">Temporary Password</label>
                <input
                  type="password"
                  required
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 focus:ring-1 focus:ring-blue-500 outline-none"
                  placeholder="Min 10 chars, uppercase, lowercase, number, symbol"
                />
              </div>

              <div>
                <label className="block text-slate-700 font-semibold mb-1">Assigned Enterprise Role</label>
                <select
                  value={formData.role}
                  onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 focus:ring-1 focus:ring-blue-500 outline-none bg-white"
                >
                  <option value="VIEWER">VIEWER (Read-Only Dashboards)</option>
                  <option value="CLOUD_ENGINEER">CLOUD_ENGINEER (Inventory & Playbooks)</option>
                  <option value="FINOPS_ANALYST">FINOPS_ANALYST (Anomalies & Recommendations)</option>
                  <option value="FINOPS_MANAGER">FINOPS_MANAGER (Approve Recommendations & Rules)</option>
                  <option value="SECURITY_AUDITOR">SECURITY_AUDITOR (Security Logs & Audit Chaining)</option>
                  <option value="ORGANIZATION_ADMIN">ORGANIZATION_ADMIN (Tenant Admin & User Management)</option>
                  <option value="SUPER_ADMIN">SUPER_ADMIN (Full Platform Authority)</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-700 font-semibold mb-1">Department</label>
                <input
                  type="text"
                  value={formData.department || ''}
                  onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 focus:ring-1 focus:ring-blue-500 outline-none"
                  placeholder="e.g. Cloud Operations / FinOps"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsCreateModalOpen(false)}
                  className="px-4 py-2 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700 shadow-xs"
                >
                  Create User
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit User Modal */}
      {editingUser && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200">
            <h2 className="text-base font-bold text-slate-900 mb-1">Edit User Profile</h2>
            <p className="text-xs text-slate-500 mb-4">{editingUser.email}</p>
            <form onSubmit={handleUpdateUser} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Full Name</label>
                <input
                  type="text"
                  value={editingUser.full_name}
                  onChange={(e) => setEditingUser({ ...editingUser, full_name: e.target.value })}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 focus:ring-1 focus:ring-blue-500 outline-none"
                />
              </div>

              <div>
                <label className="block text-slate-700 font-semibold mb-1">Enterprise Role</label>
                <select
                  value={editingUser.role}
                  onChange={(e) => setEditingUser({ ...editingUser, role: e.target.value })}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 focus:ring-1 focus:ring-blue-500 outline-none bg-white"
                >
                  <option value="VIEWER">VIEWER</option>
                  <option value="CLOUD_ENGINEER">CLOUD_ENGINEER</option>
                  <option value="FINOPS_ANALYST">FINOPS_ANALYST</option>
                  <option value="FINOPS_MANAGER">FINOPS_MANAGER</option>
                  <option value="SECURITY_AUDITOR">SECURITY_AUDITOR</option>
                  <option value="ORGANIZATION_ADMIN">ORGANIZATION_ADMIN</option>
                  <option value="SUPER_ADMIN">SUPER_ADMIN</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-700 font-semibold mb-1">Department</label>
                <input
                  type="text"
                  value={editingUser.department || ''}
                  onChange={(e) => setEditingUser({ ...editingUser, department: e.target.value })}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 focus:ring-1 focus:ring-blue-500 outline-none"
                />
              </div>

              <div className="space-y-2 pt-2 border-t border-slate-100">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={editingUser.is_active}
                    onChange={(e) => setEditingUser({ ...editingUser, is_active: e.target.checked })}
                    className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="font-semibold text-slate-700">Account Active</span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={editingUser.is_locked}
                    onChange={(e) => setEditingUser({ ...editingUser, is_locked: e.target.checked })}
                    className="rounded border-slate-300 text-rose-600 focus:ring-rose-500"
                  />
                  <span className="font-semibold text-slate-700">Account Locked (Brute Force Lockout)</span>
                </label>
              </div>

              <div className="flex items-center justify-end gap-2 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setEditingUser(null)}
                  className="px-4 py-2 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700 shadow-xs"
                >
                  Save Changes
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

