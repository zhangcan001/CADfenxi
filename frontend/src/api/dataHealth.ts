import { apiGet, apiPost } from "./client";

export type DataHealthStatus = "ok" | "info" | "warning" | "error";

export type DataHealthItem = {
  scope: string;
  check_name: string;
  status: DataHealthStatus;
  message: string;
  error_code: string | null;
  path: string | null;
  record_type: string | null;
  record_id: number | null;
  project_id: number | null;
  suggestion: string | null;
};

export type OrphanFileItem = {
  project_id: number;
  path: string;
  size_bytes: number;
  suggestion: string;
};

export type DataHealthSummary = {
  ok_count: number;
  info_count: number;
  warning_count: number;
  error_count: number;
  checked_file_count: number;
  missing_file_count: number;
  orphan_file_count: number;
  orphan_file_size_bytes: number;
  temp_file_count: number;
  temp_size_bytes: number;
  project_count: number;
  backup_count: number;
  export_count: number;
  restore_count: number;
};

export type DataHealthGroupSummary = {
  error: number;
  warning: number;
  info: number;
};

export type SystemHealthResult = {
  status: DataHealthStatus;
  generated_at: string;
  app_data_path: string;
  summary: DataHealthSummary;
  grouped_summary: Record<string, DataHealthGroupSummary>;
  items: DataHealthItem[];
};

export type ProjectHealthResult = {
  project_id: number;
  project_name: string;
  status: DataHealthStatus;
  generated_at: string;
  project_path: string;
  summary: DataHealthSummary;
  grouped_summary: Record<string, DataHealthGroupSummary>;
  items: DataHealthItem[];
  orphan_files: OrphanFileItem[];
};

export type OrphanFileScanResult = {
  project_id: number;
  status: DataHealthStatus;
  generated_at: string;
  summary: DataHealthSummary;
  grouped_summary: Record<string, DataHealthGroupSummary>;
  orphan_files: OrphanFileItem[];
};

export type TempCleanupResult = {
  status: DataHealthStatus;
  deleted_file_count: number;
  deleted_dir_count: number;
  freed_bytes: number;
  errors: string[];
};

export type DataSafetySummary = {
  app_data_path: string;
  database_exists: boolean;
  projects_dir_exists: boolean;
  backups_dir_exists: boolean;
  logs_dir_exists: boolean;
  temp_dir_exists: boolean;
  project_count: number;
  backup_count: number;
  export_count: number;
  restore_count: number;
  app_data_writable: boolean;
};

export type MaintenanceReportResult = {
  status: DataHealthStatus;
  generated_at: string;
  report_markdown: string;
  system_health: SystemHealthResult;
};

export function runSystemHealthCheck(): Promise<SystemHealthResult> {
  return apiGet<SystemHealthResult>("/api/system/health-check", { timeoutMs: 120_000 });
}

export function runProjectHealthCheck(projectId: number): Promise<ProjectHealthResult> {
  return apiGet<ProjectHealthResult>(`/api/projects/${projectId}/health-check`, { timeoutMs: 120_000 });
}

export function scanProjectOrphanFiles(projectId: number): Promise<OrphanFileScanResult> {
  return apiGet<OrphanFileScanResult>(`/api/projects/${projectId}/orphan-files`, { timeoutMs: 120_000 });
}

export function cleanupTempFiles(): Promise<TempCleanupResult> {
  return apiPost<TempCleanupResult>("/api/system/cleanup-temp", undefined, { timeoutMs: 120_000 });
}

export function getDataSafetySummary(): Promise<DataSafetySummary> {
  return apiGet<DataSafetySummary>("/api/system/data-safety-summary");
}

export function buildMaintenanceReport(): Promise<MaintenanceReportResult> {
  return apiGet<MaintenanceReportResult>("/api/system/maintenance-report", { timeoutMs: 120_000 });
}
