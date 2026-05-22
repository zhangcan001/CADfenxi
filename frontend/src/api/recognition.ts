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

async function postResult<T>(url: string): Promise<T> {
  const response = await fetch(url, { method: "POST" });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function extractSheetText(sheetId: number): Promise<RecognitionRunResult> {
  return postResult<RecognitionRunResult>(`/api/sheets/${sheetId}/extract-text`);
}

export function ocrSheetTitle(sheetId: number): Promise<RecognitionRunResult> {
  return postResult<RecognitionRunResult>(`/api/sheets/${sheetId}/ocr-title`);
}

export function extractBatchText(batchId: number): Promise<BatchRecognitionResult> {
  return postResult<BatchRecognitionResult>(`/api/imports/${batchId}/extract-text`);
}

export function ocrBatchTitles(batchId: number): Promise<BatchRecognitionResult> {
  return postResult<BatchRecognitionResult>(`/api/imports/${batchId}/ocr-titles`);
}

export async function listRecognitionRuns(sheetId: number): Promise<RecognitionRun[]> {
  const response = await fetch(`/api/sheets/${sheetId}/recognition-runs`);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json() as Promise<RecognitionRun[]>;
}
