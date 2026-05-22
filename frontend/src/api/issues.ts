import { apiGet, apiPatch } from "./client";
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

export function listProjectIssues(
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
  return apiGet<PaginatedIssues>(
    `/api/projects/${projectId}/issues${queryString ? `?${queryString}` : ""}`
  );
}

export function updateIssue(
  issueId: number,
  payload: { status: string; note?: string }
): Promise<DrawingIssue> {
  return apiPatch<DrawingIssue>(`/api/issues/${issueId}`, payload);
}
