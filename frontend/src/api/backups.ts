import { apiDelete, apiGet, apiPost } from "./client";

export type BackupRecord = {
  backup_id: number;
  project_id: number;
  backup_type: string;
  file_name: string;
  file_path: string;
  file_size: number;
  status: string;
  created_at: string;
  error_code: string | null;
  error_message: string | null;
  download_url: string;
};

export type ProjectBackupResult = {
  backup_id: number;
  project_id: number;
  file_name: string;
  file_path: string;
  file_size: number;
  created_at: string;
  download_url: string;
};

export type RestoreRecord = {
  restore_id: number;
  source_backup_id: number | null;
  source_project_name: string | null;
  new_project_id: number | null;
  restore_mode: string;
  status: string;
  created_at: string;
  error_code: string | null;
  error_message: string | null;
};

export type RestoreBackupResult = {
  restore_id: number;
  backup_id: number;
  source_project_name: string;
  new_project_id: number;
  new_project_name: string;
  status: string;
  restored_counts: Record<string, number>;
  created_at: string;
};

export type BackupVerifyResult = {
  backup_id: number | null;
  valid: boolean;
  warnings: string[];
  errors: string[];
  counts: {
    manifest_files?: number;
    missing_files?: number;
    checksum_failed?: number;
    manifest_count_mismatches?: number;
  };
  summary: {
    has_manifest: boolean;
    has_project_data: boolean;
    file_count: number;
    missing_file_count: number;
    checksum_failed_count: number;
  };
};

export type ProjectIntegrityResult = {
  project_id: number;
  valid: boolean;
  warnings: string[];
  errors: string[];
  path_check: {
    invalid_paths: number;
    missing_files: number;
  };
  counts: Record<string, number>;
};

export function createProjectBackup(projectId: number): Promise<ProjectBackupResult> {
  return apiPost<ProjectBackupResult>(`/api/projects/${projectId}/backup`, undefined, {
    timeoutMs: 120_000
  });
}

export function listBackups(): Promise<BackupRecord[]> {
  return apiGet<BackupRecord[]>("/api/backups");
}

export function listProjectBackups(projectId: number): Promise<BackupRecord[]> {
  return apiGet<BackupRecord[]>(`/api/projects/${projectId}/backups`);
}

export function downloadBackupUrl(backupId: number) {
  return `/api/backups/${backupId}/download`;
}

export function downloadBackup(backupId: number) {
  window.location.href = downloadBackupUrl(backupId);
}

export function deleteBackup(backupId: number): Promise<void> {
  return apiDelete<void>(`/api/backups/${backupId}`);
}

export function restoreBackupAsNewProject(backupId: number): Promise<RestoreBackupResult> {
  return apiPost<RestoreBackupResult>(
    `/api/backups/${backupId}/restore`,
    { restore_mode: "new_project" },
    { timeoutMs: 120_000 }
  );
}

export function listRestores(): Promise<RestoreRecord[]> {
  return apiGet<RestoreRecord[]>("/api/restores");
}

export function verifyBackup(backupId: number): Promise<BackupVerifyResult> {
  return apiGet<BackupVerifyResult>(`/api/backups/${backupId}/verify`);
}

export function checkProjectIntegrity(projectId: number): Promise<ProjectIntegrityResult> {
  return apiGet<ProjectIntegrityResult>(`/api/projects/${projectId}/integrity-check`);
}
