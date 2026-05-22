import type { DrawingIssue, FieldValue } from "./fusion";

export type AuditLog = {
  id: number;
  project_id: number;
  batch_id: number;
  file_id: number;
  sheet_id: number;
  field_name: string | null;
  old_value: string | null;
  new_value: string | null;
  action_type: string;
  operator: string;
  note: string | null;
  created_at: string;
};

export type ReviewUpdateResult = {
  sheet_id: number;
  updated_fields: FieldValue[];
  confidence_score: number;
  trust_level: string;
  issues: DrawingIssue[];
};

export type ConfirmSheetResult = {
  sheet_id: number;
  status: string;
  review_status: string;
  forced_confirm: boolean;
};

export type BatchConfirmResult = {
  project_id: number | null;
  requested_count: number;
  confirmed_count: number;
  skipped_count: number;
  items: Array<{ sheet_id: number; status: string; reason?: string }>;
  skipped: Array<{ sheet_id: number; reason: string }>;
};

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options
  });
  if (!response.ok) {
    let message = `Request failed: ${response.status}`;
    try {
      const data = (await response.json()) as { detail?: unknown };
      if (typeof data.detail === "string") {
        message = `HTTP_${response.status}：${data.detail}`;
      } else if (data.detail && typeof data.detail === "object") {
        const detail = data.detail as { message?: string; errors?: string[] };
        message = `HTTP_${response.status}：${detail.message ?? JSON.stringify(data.detail)}`;
      }
    } catch {
      message = `HTTP_${response.status}：请求失败`;
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export function updateSheetFields(
  sheetId: number,
  payload: { fields: Record<string, string>; note?: string }
): Promise<ReviewUpdateResult> {
  return request<ReviewUpdateResult>(`/api/sheets/${sheetId}/fields`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export function adoptCandidate(
  sheetId: number,
  candidateId: number,
  note?: string
): Promise<{ field_value: FieldValue; confidence_score: number; trust_level: string; issues: DrawingIssue[] }> {
  return request(`/api/sheets/${sheetId}/adopt-candidate`, {
    method: "POST",
    body: JSON.stringify({ candidate_id: candidateId, note })
  });
}

export function restoreRecommendedField(
  sheetId: number,
  fieldName: string,
  note?: string
): Promise<{ field_value: FieldValue; confidence_score: number; trust_level: string; issues: DrawingIssue[] }> {
  return request(`/api/sheets/${sheetId}/restore-recommended`, {
    method: "POST",
    body: JSON.stringify({ field_name: fieldName, note })
  });
}

export function confirmSheet(
  sheetId: number,
  payload: { force?: boolean; note?: string }
): Promise<ConfirmSheetResult> {
  return request<ConfirmSheetResult>(`/api/sheets/${sheetId}/confirm`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function batchConfirmProject(
  projectId: number,
  payload: { sheet_ids: number[]; confirm_mode?: string; only_without_errors?: boolean; note?: string }
): Promise<BatchConfirmResult> {
  return request<BatchConfirmResult>(`/api/projects/${projectId}/batch-confirm`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function getSheetAuditLogs(sheetId: number): Promise<AuditLog[]> {
  return request<AuditLog[]>(`/api/sheets/${sheetId}/audit-logs`);
}
