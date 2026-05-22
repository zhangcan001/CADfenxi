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

async function postResult<T>(url: string): Promise<T> {
  const response = await fetch(url, { method: "POST" });
  if (!response.ok) {
    throw await readApiError(response);
  }
  return response.json() as Promise<T>;
}

export function generateSheetCandidates(sheetId: number): Promise<CandidateGenerateResult> {
  return postResult<CandidateGenerateResult>(`/api/sheets/${sheetId}/generate-candidates`);
}

export function generateBatchCandidates(batchId: number): Promise<BatchCandidateGenerateResult> {
  return postResult<BatchCandidateGenerateResult>(`/api/imports/${batchId}/generate-candidates`);
}

export async function listSheetCandidates(sheetId: number): Promise<RecognitionCandidate[]> {
  const response = await fetch(`/api/sheets/${sheetId}/candidates`);
  if (!response.ok) {
    throw await readApiError(response);
  }
  return response.json() as Promise<RecognitionCandidate[]>;
}
import { readApiError } from "./errors";
