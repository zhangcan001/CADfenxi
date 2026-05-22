import { apiGet, apiPatch, apiPost } from "./client";
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

export function updateSheetFields(
  sheetId: number,
  payload: { fields: Record<string, string>; note?: string }
): Promise<ReviewUpdateResult> {
  return apiPatch<ReviewUpdateResult>(`/api/sheets/${sheetId}/fields`, payload);
}

export function adoptCandidate(
  sheetId: number,
  candidateId: number,
  note?: string
): Promise<{ field_value: FieldValue; confidence_score: number; trust_level: string; issues: DrawingIssue[] }> {
  return apiPost(`/api/sheets/${sheetId}/adopt-candidate`, { candidate_id: candidateId, note });
}

export function restoreRecommendedField(
  sheetId: number,
  fieldName: string,
  note?: string
): Promise<{ field_value: FieldValue; confidence_score: number; trust_level: string; issues: DrawingIssue[] }> {
  return apiPost(`/api/sheets/${sheetId}/restore-recommended`, { field_name: fieldName, note });
}

export function confirmSheet(
  sheetId: number,
  payload: { force?: boolean; note?: string }
): Promise<ConfirmSheetResult> {
  return apiPost<ConfirmSheetResult>(`/api/sheets/${sheetId}/confirm`, payload);
}

export function batchConfirmProject(
  projectId: number,
  payload: { sheet_ids: number[]; confirm_mode?: string; only_without_errors?: boolean; note?: string }
): Promise<BatchConfirmResult> {
  return apiPost<BatchConfirmResult>(`/api/projects/${projectId}/batch-confirm`, payload);
}

export function getSheetAuditLogs(sheetId: number): Promise<AuditLog[]> {
  return apiGet<AuditLog[]>(`/api/sheets/${sheetId}/audit-logs`);
}
