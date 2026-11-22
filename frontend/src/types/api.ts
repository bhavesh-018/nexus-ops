export type Role = "viewer" | "operator" | "admin";
export type Environment = "development" | "staging" | "production";
export type Tier = "tier1" | "tier2" | "tier3";
export type ServiceStatus = "unknown" | "healthy" | "degraded" | "down";
export type MetricName =
  | "cpu_percent"
  | "memory_percent"
  | "network_in_bytes"
  | "network_out_bytes"
  | "latency_p95_ms"
  | "error_rate_percent"
  | "availability_percent";
export type Operator = "gt" | "gte" | "lt" | "lte";
export type Severity = "info" | "warning" | "critical";

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface RegisterRequest {
  organization_name: string;
  email: string;
  password: string;
  full_name: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface User {
  id: string;
  organization_id: string;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
  created_at: string;
}

export interface UserCreate {
  email: string;
  password: string;
  full_name: string;
  role: Role;
}

export interface Service {
  id: string;
  organization_id: string;
  name: string;
  slug: string;
  environment: Environment;
  tier: Tier;
  status: ServiceStatus;
  health_url: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ServiceCreate {
  name: string;
  environment: Environment;
  tier: Tier;
  health_url?: string | null;
  metadata?: Record<string, unknown>;
}

export interface ServiceUpdate {
  name?: string;
  environment?: Environment;
  tier?: Tier;
  health_url?: string | null;
  metadata?: Record<string, unknown>;
}

export interface MonitoringConfig {
  id: string;
  service_id: string;
  metric_name: MetricName;
  operator: Operator;
  threshold_value: number;
  window_seconds: number;
  severity: Severity;
  enabled: boolean;
}

export interface MonitoringConfigCreate {
  metric_name: MetricName;
  operator: Operator;
  threshold_value: number;
  window_seconds: number;
  severity: Severity;
  enabled?: boolean;
}

export interface MonitoringConfigUpdate {
  operator?: Operator;
  threshold_value?: number;
  window_seconds?: number;
  enabled?: boolean;
}

export interface AuditLog {
  id: string;
  actor_id: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  details: Record<string, unknown>;
  ip_address: string | null;
  created_at: string;
}
