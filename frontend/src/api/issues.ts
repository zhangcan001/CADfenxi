import type { DrawingIssue } from "./fusion";

export type IssueQuery = {
  severity?: string;
  status?: string;
  issue_code?: string;
  sheet_id?: number;
  keyword?: string;
  page?: number;
  page_size?: number;
};

export type PaginatedIssues = {
  items: DrawingIssue[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};

export async function listProjectIssues(
  projectId: number,
  query: IssueQuery = {}
): Promise<PaginatedIssues> {
  const params = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (value !== undefined && value !== "" && value !== null) {
      params.set(key, String(value));
    }
  });
  const queryString = params.toString();
  const response = await fetch(
    `/api/projects/${projectId}/issues${queryString ? `?${queryString}` : ""}`
  );
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json() as Promise<PaginatedIssues>;
}

export async function updateIssue(
  issueId: number,
  payload: { status: string; note?: string }
): Promise<DrawingIssue> {
  const response = await fetch(`/api/issues/${issueId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json() as Promise<DrawingIssue>;
}
