/**
 * CloudSage Enterprise RBAC and Security API Client.
 */

import axios from 'axios';
import {
  CurrentUser,
  TokenResponse,
  UserSummary,
  UserDetail,
  UserCreatePayload,
  UserUpdatePayload,
  RoleDetail,
  Permission,
  ApprovalRequest,
  ApprovalDecisionPayload,
  SecurityEvent,
  SecurityStats,
  AuditIntegrityReport,
  AuditVerificationResult,
  AuditCheckpoint,
} from '../types/security';

const API_BASE = '/api/v1';

export const securityAxios = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach JWT access token to every outgoing request if available
securityAxios.interceptors.request.use((config) => {
  const token = localStorage.getItem('cloudsage_access_token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 unauthorized responses
securityAxios.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Clear expired auth session
      localStorage.removeItem('cloudsage_access_token');
      localStorage.removeItem('cloudsage_refresh_token');
      localStorage.removeItem('cloudsage_user');
    }
    return Promise.reject(error);
  }
);

export const SecurityAuth = {
  getStoredToken(): string | null {
    return localStorage.getItem('cloudsage_access_token');
  },

  getStoredUser(): CurrentUser | null {
    const raw = localStorage.getItem('cloudsage_user');
    if (!raw) return null;
    try {
      return JSON.parse(raw) as CurrentUser;
    } catch {
      return null;
    }
  },

  setAuthData(data: TokenResponse): void {
    localStorage.setItem('cloudsage_access_token', data.access_token);
    localStorage.setItem('cloudsage_refresh_token', data.refresh_token);
    localStorage.setItem('cloudsage_user', JSON.stringify(data.user));
  },

  clearAuthData(): void {
    localStorage.removeItem('cloudsage_access_token');
    localStorage.removeItem('cloudsage_refresh_token');
    localStorage.removeItem('cloudsage_user');
  },

  async login(email: string, password: string): Promise<TokenResponse> {
    const res = await securityAxios.post<TokenResponse>('/auth/login', {
      email,
      password,
    });
    this.setAuthData(res.data);
    return res.data;
  },

  async refreshToken(): Promise<TokenResponse> {
    const refreshToken = localStorage.getItem('cloudsage_refresh_token');
    if (!refreshToken) throw new Error('No refresh token available');
    const res = await securityAxios.post<TokenResponse>('/auth/refresh', {
      refresh_token: refreshToken,
    });
    this.setAuthData(res.data);
    return res.data;
  },

  async logout(): Promise<void> {
    try {
      await securityAxios.post('/auth/logout');
    } finally {
      this.clearAuthData();
    }
  },

  async getCurrentUser(): Promise<CurrentUser> {
    const res = await securityAxios.get<CurrentUser>('/auth/me');
    localStorage.setItem('cloudsage_user', JSON.stringify(res.data));
    return res.data;
  },

  hasPermission(permission: string): boolean {
    const user = this.getStoredUser();
    if (!user) return false;
    if (user.role === 'SUPER_ADMIN' || user.permissions.includes('*')) {
      return true;
    }
    return user.permissions.includes(permission);
  },

  hasRole(role: string): boolean {
    const user = this.getStoredUser();
    if (!user) return false;
    if (user.role === 'SUPER_ADMIN') return true;
    return user.role === role || user.roles.includes(role);
  },
};

export const UserAdminService = {
  async listUsers(params?: {
    search?: string;
    role?: string;
    is_active?: boolean;
    skip?: number;
    limit?: number;
  }): Promise<UserSummary[]> {
    const res = await securityAxios.get<UserSummary[]>('/admin/users', { params });
    return res.data;
  },

  async getUser(id: string): Promise<UserDetail> {
    const res = await securityAxios.get<UserDetail>(`/admin/users/${id}`);
    return res.data;
  },

  async createUser(payload: UserCreatePayload): Promise<UserDetail> {
    const res = await securityAxios.post<UserDetail>('/admin/users', payload);
    return res.data;
  },

  async updateUser(id: string, payload: UserUpdatePayload): Promise<UserDetail> {
    const res = await securityAxios.patch<UserDetail>(`/admin/users/${id}`, payload);
    return res.data;
  },

  async revokeUserSessions(id: string): Promise<{ status: string; revoked_count: number }> {
    const res = await securityAxios.post(`/admin/users/${id}/revoke-sessions`);
    return res.data;
  },
};

export const RoleAdminService = {
  async listRoles(): Promise<RoleDetail[]> {
    const res = await securityAxios.get<RoleDetail[]>('/admin/roles');
    return res.data;
  },

  async getRole(id: string): Promise<RoleDetail> {
    const res = await securityAxios.get<RoleDetail>(`/admin/roles/${id}`);
    return res.data;
  },

  async listPermissions(): Promise<Permission[]> {
    const res = await securityAxios.get<Permission[]>('/admin/roles/permissions');
    return res.data;
  },
};

export const SecurityGovernanceService = {
  async getSecurityStats(): Promise<SecurityStats> {
    const res = await securityAxios.get<SecurityStats>('/admin/security/stats');
    return res.data;
  },

  async listSecurityEvents(params?: {
    severity?: string;
    event_type?: string;
    actor_email?: string;
    limit?: number;
  }): Promise<SecurityEvent[]> {
    const res = await securityAxios.get<SecurityEvent[]>('/admin/security/events', { params });
    return res.data;
  },

  async listApprovals(params?: { status?: string; limit?: number }): Promise<ApprovalRequest[]> {
    const res = await securityAxios.get<ApprovalRequest[]>('/admin/security/approvals', { params });
    return res.data;
  },

  async decideApproval(
    id: string,
    payload: ApprovalDecisionPayload
  ): Promise<ApprovalRequest> {
    const res = await securityAxios.post<ApprovalRequest>(
      `/admin/security/approvals/${id}/decide`,
      payload
    );
    return res.data;
  },

  async getAuditIntegrityReport(): Promise<AuditIntegrityReport> {
    const res = await securityAxios.get<AuditIntegrityReport>('/admin/security/audit-integrity');
    return res.data;
  },

  async verifyAuditChain(limit?: number): Promise<AuditVerificationResult> {
    const res = await securityAxios.post<AuditVerificationResult>(
      '/admin/security/audit-integrity/verify',
      null,
      { params: { limit } }
    );
    return res.data;
  },

  async listAuditCheckpoints(): Promise<AuditCheckpoint[]> {
    const res = await securityAxios.get<AuditCheckpoint[]>('/admin/security/audit-checkpoints');
    return res.data;
  },

  async createAuditCheckpoint(notes?: string): Promise<AuditCheckpoint> {
    const res = await securityAxios.post<AuditCheckpoint>(
      '/admin/security/audit-checkpoints',
      { notes }
    );
    return res.data;
  },
};
