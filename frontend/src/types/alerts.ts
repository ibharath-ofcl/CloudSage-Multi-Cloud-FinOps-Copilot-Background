/**
 * CloudSage Alerting & Enterprise Notification Hub TypeScript Type Definitions.
 * Aligned with backend/app/schemas/alert.py.
 */

export type AlertSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type AlertLifecycleStatus = 'OPEN' | 'ACKNOWLEDGED' | 'INVESTIGATING' | 'RESOLVED' | 'SUPPRESSED' | 'CLOSED';
export type NotificationDeliveryStatus = 'PENDING' | 'PROCESSING' | 'SENT' | 'DELIVERED' | 'FAILED' | 'RETRYING' | 'DEAD_LETTERED' | 'CANCELLED';
export type NotificationChannelType = 'IN_APP' | 'EMAIL' | 'WEBHOOK' | 'SLACK' | 'TEAMS';

export interface AlertRule {
  id: string;
  name: string;
  description?: string | null;
  alert_type: string;
  provider: 'AWS' | 'AZURE' | 'GCP' | 'ALL';
  account_id?: string | null;
  region?: string | null;
  service_name?: string | null;
  environment?: string | null;
  owner?: string | null;
  cost_center?: string | null;
  min_severity: AlertSeverity;
  threshold_value: string | number;
  min_excess_cost: string | number;
  percentage_deviation_threshold: string | number;
  absolute_deviation_threshold: string | number;
  anomaly_category?: string | null;
  channels: NotificationChannelType[];
  recipients: string[];
  cooldown_minutes: number;
  escalation_policy: Record<string, any>;
  is_enabled: boolean;
  is_archived: boolean;
  created_by: string;
  updated_by?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AlertRuleCreate {
  name: string;
  description?: string;
  alert_type?: string;
  provider?: string;
  account_id?: string;
  region?: string;
  service_name?: string;
  environment?: string;
  owner?: string;
  cost_center?: string;
  min_severity?: AlertSeverity;
  threshold_value?: number;
  min_excess_cost?: number;
  percentage_deviation_threshold?: number;
  absolute_deviation_threshold?: number;
  anomaly_category?: string;
  channels?: NotificationChannelType[];
  recipients?: string[];
  cooldown_minutes?: number;
  escalation_policy?: Record<string, any>;
  is_enabled?: boolean;
}

export interface AlertRuleUpdate {
  name?: string;
  description?: string;
  provider?: string;
  account_id?: string;
  region?: string;
  service_name?: string;
  environment?: string;
  owner?: string;
  cost_center?: string;
  min_severity?: AlertSeverity;
  threshold_value?: number;
  min_excess_cost?: number;
  percentage_deviation_threshold?: number;
  absolute_deviation_threshold?: number;
  anomaly_category?: string;
  channels?: NotificationChannelType[];
  recipients?: string[];
  cooldown_minutes?: number;
  escalation_policy?: Record<string, any>;
  is_enabled?: boolean;
}

export interface AlertRuleListResponse {
  items: AlertRule[];
  total: number;
}

export interface AlertRulePreviewRequest {
  provider?: string;
  account_id?: string;
  min_severity?: AlertSeverity;
  min_excess_cost?: number;
  percentage_deviation_threshold?: number;
  sample_limit?: number;
}

export interface AlertRulePreviewMatch {
  anomaly_id: string;
  title: string;
  provider: string;
  account_id: string;
  service_name: string;
  excess_cost: string | number;
  percentage_deviation: string | number;
  severity: AlertSeverity;
  detected_at: string;
}

export interface AlertRulePreviewResponse {
  matched_count: number;
  total_evaluated: number;
  sample_matches: AlertRulePreviewMatch[];
}

export interface AlertInstance {
  id: string;
  alert_rule_id?: string | null;
  anomaly_id: string;
  dedup_key: string;
  title: string;
  severity: AlertSeverity;
  current_cost: string | number;
  expected_cost: string | number;
  excess_cost: string | number;
  percentage_deviation: string | number;
  status: AlertLifecycleStatus;
  provider: 'AWS' | 'AZURE' | 'GCP';
  account_id: string;
  service_name: string;
  region: string;
  resource_id?: string | null;
  acknowledged_by?: string | null;
  acknowledged_at?: string | null;
  investigated_by?: string | null;
  investigation_notes?: string | null;
  ticket_ref?: string | null;
  resolved_by?: string | null;
  resolved_at?: string | null;
  resolution_notes?: string | null;
  suppressed_by?: string | null;
  suppress_reason?: string | null;
  suppress_until?: string | null;
  trigger_count: number;
  first_triggered_at: string;
  last_triggered_at: string;
  escalation_level: number;
  last_escalated_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AlertInstanceListResponse {
  items: AlertInstance[];
  total: number;
}

export interface AlertHistory {
  id: string;
  alert_instance_id: string;
  previous_status?: string | null;
  new_status: string;
  action: string;
  actor: string;
  notes?: string | null;
  created_at: string;
}

export interface AlertInstanceDetail extends AlertInstance {
  history: AlertHistory[];
  deliveries: NotificationOutbox[];
  anomaly?: Record<string, any> | null;
}

export interface AlertStats {
  total_alerts: number;
  active_alerts: number;
  critical_alerts: number;
  high_alerts: number;
  unacknowledged_alerts: number;
  investigating_alerts: number;
  resolved_alerts: number;
  suppressed_alerts: number;
  delivery_failures_24h: number;
}

export interface AlertActionRequest {
  action: 'ACKNOWLEDGE' | 'INVESTIGATE' | 'RESOLVE' | 'SUPPRESS' | 'REOPEN' | 'CLOSE';
  notes?: string;
  suppress_hours?: number;
  ticket_ref?: string;
}

export interface InAppNotification {
  id: string;
  alert_instance_id?: string | null;
  recipient_user_id: string;
  title: string;
  message: string;
  severity: AlertSeverity;
  provider: string;
  account_id: string;
  service_name: string;
  excess_cost: string | number;
  is_read: boolean;
  read_at?: string | null;
  action_url?: string | null;
  created_at: string;
}

export interface InAppNotificationListResponse {
  items: InAppNotification[];
  total: number;
  unread_count: number;
}

export interface UnreadCountResponse {
  unread_count: number;
}

export interface NotificationDeliveryAttempt {
  id: string;
  outbox_id: string;
  attempt_number: number;
  channel: string;
  recipient: string;
  status: string;
  response_code?: number | null;
  response_body?: string | null;
  latency_ms?: number | null;
  error_message?: string | null;
  attempted_at: string;
}

export interface NotificationOutbox {
  id: string;
  alert_instance_id?: string | null;
  channel: string;
  recipient: string;
  subject: string;
  payload: Record<string, any>;
  status: NotificationDeliveryStatus;
  attempts: number;
  max_attempts: number;
  next_attempt_at: string;
  last_attempt_at?: string | null;
  last_error?: string | null;
  created_at: string;
  delivered_at?: string | null;
  delivery_attempts?: NotificationDeliveryAttempt[];
}

export interface NotificationOutboxListResponse {
  items: NotificationOutbox[];
  total: number;
}

export interface NotificationHealth {
  status: 'HEALTHY' | 'DEGRADED' | 'CRITICAL';
  in_app_operational: boolean;
  email_mode: string;
  webhook_operational: boolean;
  pending_outbox_count: number;
  dead_letter_count: number;
  total_delivered_24h: number;
  total_failed_24h: number;
}

export interface NotificationPreference {
  id: string;
  user_email: string;
  enabled_channels: string[];
  min_severity: string;
  receive_digests: boolean;
  digest_frequency: 'IMMEDIATE' | 'DAILY' | 'WEEKLY';
  quiet_hours_enabled: boolean;
  quiet_hours_start_utc?: string | null;
  quiet_hours_end_utc?: string | null;
  created_at: string;
  updated_at: string;
}
