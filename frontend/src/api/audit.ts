import type { AuditLog } from "../types/api";
import { apiRequest } from "./client";

export async function listAuditLogs(limit = 20): Promise<AuditLog[]> {
  return apiRequest<AuditLog[]>(`/api/v1/audit-logs?limit=${limit}`);
}
