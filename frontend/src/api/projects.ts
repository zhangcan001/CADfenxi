import { apiDelete, apiGet, apiPatch, apiPost } from "./client";

export type ProjectStats = {
  file_count: number;
  sheet_count: number;
  preprocessed_count: number;
  recognized_count: number;
  need_review_count: number;
  confirmed_count: number;
  failed_count: number;
  issue_count: number;
  error_issue_count: number;
  warning_issue_count: number;
  trust_level_a_count: number;
  trust_level_b_count: number;
  trust_level_c_count: number;
  trust_level_d_count: number;
};

export type Project = {
  id: number;
  name: string;
  description: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  last_opened_at: string | null;
  stats: ProjectStats;
};

export type ProjectWorkbenchSummary = {
  project_id: number;
  drawing_file_count: number;
  drawing_sheet_count: number;
  unreviewed_count: number;
  low_confidence_count: number;
  missing_drawing_no_count: number;
  missing_drawing_name_count: number;
  open_error_count: number;
  open_warning_count: number;
  cad_preview_missing_count: number;
  last_import_at: string | null;
  last_export_at: string | null;
  last_backup_at: string | null;
};

export type ProjectPayload = {
  name: string;
  description?: string;
};

export function createProject(payload: ProjectPayload): Promise<Project> {
  return apiPost<Project>("/api/projects", payload);
}

export function listProjects(): Promise<Project[]> {
  return apiGet<Project[]>("/api/projects");
}

export function getProject(projectId: number): Promise<Project> {
  return apiGet<Project>(`/api/projects/${projectId}`);
}

export function getProjectWorkbenchSummary(projectId: number): Promise<ProjectWorkbenchSummary> {
  return apiGet<ProjectWorkbenchSummary>(`/api/projects/${projectId}/workbench-summary`);
}

export function updateProject(
  projectId: number,
  payload: ProjectPayload
): Promise<Project> {
  return apiPatch<Project>(`/api/projects/${projectId}`, payload);
}

export function deleteProject(projectId: number): Promise<void> {
  return apiDelete<void>(`/api/projects/${projectId}`);
}
