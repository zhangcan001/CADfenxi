import { apiGet, apiPost } from "./client";

export type RecognitionCandidate = {
  id: number;
  project_id: number;
  batch_id: number;
  file_id: number;
  sheet_id: number;
  field_name: string;
  candidate_value: string;
  normalized_value: string | null;
  source_type: string;
  confidence: number;
  raw_text: string;
  bbox: string | null;
  run_id: number | null;
  parser_name: string;
  parser_version: string;
  created_at: string;
};

export type CandidateGenerateResult = {
  sheet_id: number;
  candidate_count: number;
  candidates: RecognitionCandidate[];
};

export type BatchCandidateGenerateResult = {
  batch_id: number;
  total_count: number;
  success_count: number;
  failed_count: number;
  candidate_count: number;
  items: CandidateGenerateResult[];
};

const LONG_OP_TIMEOUT_MS = 300_000;

export function generateSheetCandidates(sheetId: number): Promise<CandidateGenerateResult> {
  return apiPost<CandidateGenerateResult>(`/api/sheets/${sheetId}/generate-candidates`, undefined, {
    timeoutMs: LONG_OP_TIMEOUT_MS
  });
}

export function generateBatchCandidates(batchId: number): Promise<BatchCandidateGenerateResult> {
  return apiPost<BatchCandidateGenerateResult>(
    `/api/imports/${batchId}/generate-candidates`,
    undefined,
    { timeoutMs: LONG_OP_TIMEOUT_MS }
  );
}

export function listSheetCandidates(sheetId: number): Promise<RecognitionCandidate[]> {
  return apiGet<RecognitionCandidate[]>(`/api/sheets/${sheetId}/candidates`);
}
