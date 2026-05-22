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

async function postResult<T>(url: string): Promise<T> {
  const response = await fetch(url, { method: "POST" });
  if (!response.ok) {
    throw await readApiError(response);
  }
  return response.json() as Promise<T>;
}

export function fuseSheetFields(sheetId: number): Promise<SheetFusionResult> {
  return postResult<SheetFusionResult>(`/api/sheets/${sheetId}/fuse-fields`);
}

export function fuseBatchFields(batchId: number): Promise<BatchFusionResult> {
  return postResult<BatchFusionResult>(`/api/imports/${batchId}/fuse-fields`);
}

export async function listSheetFieldValues(sheetId: number): Promise<FieldValue[]> {
  const response = await fetch(`/api/sheets/${sheetId}/field-values`);
  if (!response.ok) {
    throw await readApiError(response);
  }
  return response.json() as Promise<FieldValue[]>;
}

export async function listSheetEvidence(sheetId: number): Promise<FieldEvidence[]> {
  const response = await fetch(`/api/sheets/${sheetId}/evidence`);
  if (!response.ok) {
    throw await readApiError(response);
  }
  return response.json() as Promise<FieldEvidence[]>;
}

export async function listProjectIssues(projectId: number): Promise<DrawingIssue[]> {
  const response = await fetch(`/api/projects/${projectId}/issues`);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  const data = (await response.json()) as { items?: DrawingIssue[] } | DrawingIssue[];
  return Array.isArray(data) ? data : data.items ?? [];
}
import { readApiError } from "./errors";
