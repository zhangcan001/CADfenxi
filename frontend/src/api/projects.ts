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

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers
    },
    ...options
  });

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export function createProject(payload: ProjectPayload): Promise<Project> {
  return request<Project>("/api/projects", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function listProjects(): Promise<Project[]> {
  return request<Project[]>("/api/projects");
}

export function getProject(projectId: number): Promise<Project> {
  return request<Project>(`/api/projects/${projectId}`);
}

export function updateProject(
  projectId: number,
  payload: ProjectPayload
): Promise<Project> {
  return request<Project>(`/api/projects/${projectId}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export function deleteProject(projectId: number): Promise<void> {
  return request<void>(`/api/projects/${projectId}`, {
    method: "DELETE"
  });
}
