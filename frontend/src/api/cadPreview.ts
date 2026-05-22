import { apiPost } from "./client";

export type CadPreviewResult = {
  file_id: number | null;
  sheet_id: number;
  file_name: string | null;
  status: string;
  cad_preview_path: string | null;
  preview_url: string | null;
  warnings: string[];
  duration_seconds: number;
  skipped_entity_count: number;
  error_code: string | null;
  error_message: string | null;
};

export type CadPreviewBatchPayload = {
  skip_completed: boolean;
  force: boolean;
  continue_on_error: boolean;
};

export type CadPreviewBatchSummary = {
  total_count: number;
  success_count: number;
  failed_count: number;
  skipped_count: number;
  warning_count: number;
  duration_seconds: number;
};

export type CadPreviewBatchError = {
  sheet_id: number | null;
  file_name: string | null;
  error_code: string;
  message: string;
};

export type BatchCadPreviewResult = {
  scope: string;
  project_id: number | null;
  batch_id: number | null;
  status: string;
  summary: CadPreviewBatchSummary;
  total_count: number;
  success_count: number;
  failed_count: number;
  skipped_count: number;
  warning_count: number;
  duration_seconds: number;
  items: CadPreviewResult[];
  errors: CadPreviewBatchError[];
  warnings: string[];
};

const LONG_OP_TIMEOUT_MS = 300_000;

export function generateCadPreview(sheetId: number): Promise<CadPreviewResult> {
  return apiPost<CadPreviewResult>(`/api/sheets/${sheetId}/cad-preview`, undefined, {
    timeoutMs: LONG_OP_TIMEOUT_MS
  });
}

export function getCadPreviewImageUrl(sheetId: number) {
  return `/api/sheets/${sheetId}/cad-preview-image`;
}

export function generateBatchCadPreview(
  batchId: number,
  payload: CadPreviewBatchPayload
): Promise<BatchCadPreviewResult> {
  return apiPost<BatchCadPreviewResult>(`/api/imports/${batchId}/cad-preview`, payload, {
    timeoutMs: LONG_OP_TIMEOUT_MS
  });
}

export function generateProjectCadPreview(
  projectId: number,
  payload: CadPreviewBatchPayload
): Promise<BatchCadPreviewResult> {
  return apiPost<BatchCadPreviewResult>(`/api/projects/${projectId}/cad-preview`, payload, {
    timeoutMs: LONG_OP_TIMEOUT_MS
  });
}
