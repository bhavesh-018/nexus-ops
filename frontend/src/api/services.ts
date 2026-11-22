import type {
  MonitoringConfig,
  MonitoringConfigCreate,
  MonitoringConfigUpdate,
  Service,
  ServiceCreate,
  ServiceUpdate
} from "../types/api";
import { apiRequest } from "./client";

export async function listServices(params?: {
  environment?: string;
  status?: string;
}): Promise<Service[]> {
  const qs = new URLSearchParams();
  if (params?.environment) qs.set("environment", params.environment);
  if (params?.status) qs.set("status", params.status);
  const query = qs.toString() ? `?${qs.toString()}` : "";
  return apiRequest<Service[]>(`/api/v1/services${query}`);
}

export async function createService(payload: ServiceCreate): Promise<Service> {
  return apiRequest<Service>("/api/v1/services", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function updateService(serviceId: string, payload: ServiceUpdate): Promise<Service> {
  return apiRequest<Service>(`/api/v1/services/${serviceId}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export async function deleteService(serviceId: string): Promise<void> {
  return apiRequest<void>(`/api/v1/services/${serviceId}`, { method: "DELETE" });
}

export async function listMonitoringConfigs(serviceId: string): Promise<MonitoringConfig[]> {
  return apiRequest<MonitoringConfig[]>(`/api/v1/services/${serviceId}/monitoring-configs`);
}

export async function createMonitoringConfig(
  serviceId: string,
  payload: MonitoringConfigCreate
): Promise<MonitoringConfig> {
  return apiRequest<MonitoringConfig>(`/api/v1/services/${serviceId}/monitoring-configs`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function updateMonitoringConfig(
  serviceId: string,
  configId: string,
  payload: MonitoringConfigUpdate
): Promise<MonitoringConfig> {
  return apiRequest<MonitoringConfig>(
    `/api/v1/services/${serviceId}/monitoring-configs/${configId}`,
    {
      method: "PATCH",
      body: JSON.stringify(payload)
    }
  );
}

export async function deleteMonitoringConfig(serviceId: string, configId: string): Promise<void> {
  return apiRequest<void>(`/api/v1/services/${serviceId}/monitoring-configs/${configId}`, {
    method: "DELETE"
  });
}
