/**
 * CloudSage Enterprise RBAC and Security Governance TypeScript Definitions.
 */

export type EnterpriseRole =
  | 'SUPER_ADMIN'
  | 'ORGANIZATION_ADMIN'
  | 'FINOPS_MANAGER'
  | 'FINOPS_ANALYST'
  | 'CLOUD_ENGINEER'
  | 'SECURITY_AUDITOR'
  | 'VIEWER'
  | 'FINOPS_ENGINEER'
  | 'FINANCE_ANALYST'
  | 'ENGINEERING_MANAGER'
  | 'EXECUTIVE';

export type SecuritySeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFORMATIONAL';

export type ApprovalStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'EXPIRED' | 'CANCELLED';

export interface CurrentUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
  roles: string[];
  permissions: string[];
  department?: string | null;
  tenant_id?: string | null;
  is_active: boolean;
  is_locked: boolean;
  created_at: string;
  last_login_at?: string | null;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: CurrentUser;
}

export interface UserSummary {
  id: string;
  email: string;
  full_name: string;
  role: string;
  roles: string[];
  department?: string | null;
  tenant_id?: string | null;
  is_active: boolean;
  is_locked: boolean;
  locked_until?: string | null;
  failed_login_attempts: number;
  created_at: string;
  last_login_at?: string | null;
}

export interface UserDetail extends UserSummary {
  permissions: string[];
  active_sessions_count: number;
}

export interface UserCreatePayload {
  email: string;
  full_name: string;
  password: string;
  role?: string;
  department?: string | null;
  tenant_id?: string | null;
}

export interface UserUpdatePayload {
  full_name?: string | null;
  role?: string | null;
  department?: string | null;
  is_active?: boolean | null;
  is_locked?: boolean | null;
  password?: string | null;
}

export interface Permission {
  id: string;
  name: string;
  resource: string;
  action: string;
  description?: string | null;
  is_system: boolean;
}

export interface RoleDetail {
  id: string;
  name: string;
  display_name: string;
  description?: string | null;
  is_system: boolean;
  is_custom: boolean;
  user_count: number;
  permissions: string[];
}

export interface UserSession {
  id: string;
  user_id: string;
  user_email?: string;
  status: 'ACTIVE' | 'REVOKED' | 'EXPIRED';
  ip_address?: string | null;
  user_agent?: string | null;
  created_at: string;
  last_active_at: string;
  expires_at: string;
}

export interface ApprovalRequest {
  id: string;
  tenant_id?: string | null;
  action_type: string;
  resource_type: string;
  resource_id?: string | null;
  requester_id: string;
  requester_email?: string | null;
  approver_id?: string | null;
  approver_email?: string | null;
  status: ApprovalStatus;
  payload: Record<string, any>;
  justification?: string | null;
  decision_notes?: string | null;
  created_at: string;
  decided_at?: string | null;
  expires_at: string;
}

export interface ApprovalDecisionPayload {
  approved: boolean;
  notes?: string | null;
}

export interface SecurityEvent {
  id: string;
  tenant_id?: string | null;
  event_type: string;
  severity: SecuritySeverity;
  actor_email?: string | null;
  ip_address?: string | null;
  resource_type?: string | null;
  action?: string | null;
  details: Record<string, any>;
  created_at: string;
}

export interface SecurityStats {
  active_users_count: number;
  locked_accounts_count: number;
  active_sessions_count: number;
  pending_approvals_count: number;
  security_events_last_24h: number;
  critical_events_last_24h: number;
  audit_chain_verified: boolean;
}

export interface AuditVerificationResult {
  chain_valid: boolean;
  records_evaluated: number;
  broken_records: string[];
  error?: string | null;
}

export interface AuditIntegrityReport {
  total_audit_records: number;
  chain_valid: boolean;
  records_checked: number;
  broken_records_count: number;
  checkpoints_count: number;
  latest_checkpoint_hash?: string | null;
  latest_checkpoint_at?: string | null;
}

export interface AuditCheckpoint {
  id: string;
  checkpoint_hash: string;
  record_count: number;
  first_audit_id?: string | null;
  last_audit_id?: string | null;
  notes?: string | null;
  created_at: string;
}
