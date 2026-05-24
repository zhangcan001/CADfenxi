import { apiGet, apiPost } from "./client";

export type RecognitionRunResult = {
  sheet_id: number;
  status: string;
  run_type: string;
  output_path: string | null;
  text_length: number;
  error_code: string | null;
  error_message: string | null;
};

export type BatchRecognitionResult = {
  batch_id: number;
  total_count: number;
  success_count: number;
  failed_count: number;
  items: RecognitionRunResult[];
};

export type RecognitionRun = {
  id: number;
  project_id: number;
  batch_id: number;
  file_id: number | null;
  sheet_id: number;
  run_type: string;
  engine_name: string;
  engine_version: string;
  status: string;
  output_path: string | null;
  started_at: string;
  finished_at: string;
  error_code: string | null;
  error_message: string | null;
  created_at: string;
};

const LONG_OP_TIMEOUT_MS = 300_000;

export function extractSheetText(sheetId: number): Promise<RecognitionRunResult> {
  return apiPost<RecognitionRunResult>(`/api/sheets/${sheetId}/extract-text`, undefined, {
    timeoutMs: LONG_OP_TIMEOUT_MS
  });
}

export function ocrSheetTitle(sheetId: number): Promise<RecognitionRunResult> {
  return apiPost<RecognitionRunResult>(`/api/sheets/${sheetId}/ocr-title`, undefined, {
    timeoutMs: LONG_OP_TIMEOUT_MS
  });
}

export function extractBatchText(batchId: number): Promise<BatchRecognitionResult> {
  return apiPost<BatchRecognitionResult>(`/api/imports/${batchId}/extract-text`, undefined, {
    timeoutMs: LONG_OP_TIMEOUT_MS
  });
}

export type OcrJobStatus = {
  batch_id: number;
  status: "idle" | "running" | "completed" | "failed";
  total: number;
  processed: number;
  success_count: number;
  failed_count: number;
  started_at: string | null;
  finished_at: string | null;
  message: string | null;
};

export function ocrBatchTitles(batchId: number): Promise<OcrJobStatus> {
  return apiPost<OcrJobStatus>(`/api/imports/${batchId}/ocr-titles`, undefined);
}

export function getOcrBatchJob(batchId: number): Promise<OcrJobStatus> {
  return apiGet<OcrJobStatus>(`/api/imports/${batchId}/ocr-job`);
}

export function listRecognitionRuns(sheetId: number): Promise<RecognitionRun[]> {
  return apiGet<RecognitionRun[]>(`/api/sheets/${sheetId}/recognition-runs`);
}
