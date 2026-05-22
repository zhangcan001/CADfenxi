import { apiGet, apiPost } from "./client";

export type FieldValue = {
  id: number;
  project_id: number;
  batch_id: number;
  file_id: number;
  sheet_id: number;
  field_name: string;
  raw_value: string;
  normalized_value: string | null;
  display_value: string;
  final_source: string;
  confidence: number;
  is_reviewed: boolean;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type FieldEvidence = {
  id: number;
  field_value_id: number;
  candidate_id: number;
  source_type: string;
  raw_text: string;
  bbox: string | null;
  confidence: number;
  created_at: string;
  field_name: string | null;
};

export type DrawingIssue = {
  id: number;
  project_id: number;
  batch_id: number;
  file_id: number;
  sheet_id: number;
  issue_code: string;
  severity: string;
  message: string;
  suggestion: string;
  status: string;
  created_at: string;
  resolved_at: string | null;
};

export type SheetFusionResult = {
  sheet_id: number;
  status: string;
  confidence_score: number;
  trust_level: string;
  field_values: FieldValue[];
  issues: DrawingIssue[];
};

export type BatchFusionResult = {
  batch_id: number;
  total_count: number;
  success_count: number;
  failed_count: number;
  issue_count: number;
  items: SheetFusionResult[];
};

const LONG_OP_TIMEOUT_MS = 300_000;

export function fuseSheetFields(sheetId: number): Promise<SheetFusionResult> {
  return apiPost<SheetFusionResult>(`/api/sheets/${sheetId}/fuse-fields`, undefined, {
    timeoutMs: LONG_OP_TIMEOUT_MS
  });
}

export function fuseBatchFields(batchId: number): Promise<BatchFusionResult> {
  return apiPost<BatchFusionResult>(`/api/imports/${batchId}/fuse-fields`, undefined, {
    timeoutMs: LONG_OP_TIMEOUT_MS
  });
}

export function listSheetFieldValues(sheetId: number): Promise<FieldValue[]> {
  return apiGet<FieldValue[]>(`/api/sheets/${sheetId}/field-values`);
}

export function listSheetEvidence(sheetId: number): Promise<FieldEvidence[]> {
  return apiGet<FieldEvidence[]>(`/api/sheets/${sheetId}/evidence`);
}
