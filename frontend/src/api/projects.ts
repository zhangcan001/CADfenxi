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

export function updateProject(
  projectId: number,
  payload: ProjectPayload
): Promise<Project> {
  return apiPatch<Project>(`/api/projects/${projectId}`, payload);
}

export function deleteProject(projectId: number): Promise<void> {
  return apiDelete<void>(`/api/projects/${projectId}`);
}
