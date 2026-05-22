import { apiGet, apiPost } from "./client";

export type DxfSheetPrepareResult = {
  file_id: number;
  sheet_id: number;
  project_id: number;
  batch_id: number;
  page_no: number;
  sheet_type: string;
  status: string;
  review_status: string;
  created: boolean;
};

export type BatchDxfSheetPrepareResult = {
  batch_id: number;
  total_dxf_count: number;
  created_count: number;
  existing_count: number;
  failed_count: number;
  items: Array<{
    file_id: number;
    sheet_id: number | null;
    status: string;
    created: boolean;
    error_code: string | null;
    message: string | null;
  }>;
};

export type CadParseResult = {
  file_id: number;
  sheet_id: number | null;
  status: string;
  run_id: number | null;
  output_path: string | null;
  counts: Record<string, number>;
  warnings: string[];
  error_code: string | null;
  error_message: string | null;
};

export type BatchCadParseResult = {
  batch_id: number;
  total_count: number;
  success_count: number;
  failed_count: number;
  skipped_count: number;
  items: CadParseResult[];
};

export type CadParseSummary = {
  sheet_id: number;
  file_id: number;
  output_path: string;
  counts: Record<string, number>;
  sample_texts: Array<Record<string, unknown>>;
  sample_mtexts: Array<Record<string, unknown>>;
  sample_attribs: Array<Record<string, unknown>>;
  layers: string[];
  warnings: string[];
};

// DXF/DWG parsing can be slow on large files.
const LONG_OP_TIMEOUT_MS = 300_000;

export function prepareDxfSheet(fileId: number): Promise<DxfSheetPrepareResult> {
  return apiPost<DxfSheetPrepareResult>(`/api/files/${fileId}/prepare-dxf-sheet`, undefined, {
    timeoutMs: LONG_OP_TIMEOUT_MS
  });
}

export function prepareDxfSheetsForBatch(batchId: number): Promise<BatchDxfSheetPrepareResult> {
  return apiPost<BatchDxfSheetPrepareResult>(
    `/api/imports/${batchId}/prepare-dxf-sheets`,
    undefined,
    { timeoutMs: LONG_OP_TIMEOUT_MS }
  );
}

export function parseDxfFile(fileId: number): Promise<CadParseResult> {
  return apiPost<CadParseResult>(`/api/files/${fileId}/parse-dxf`, undefined, {
    timeoutMs: LONG_OP_TIMEOUT_MS
  });
}

export function parseDxfBatch(batchId: number): Promise<BatchCadParseResult> {
  return apiPost<BatchCadParseResult>(`/api/imports/${batchId}/parse-dxf`, undefined, {
    timeoutMs: LONG_OP_TIMEOUT_MS
  });
}

export function getCadParseSummary(sheetId: number): Promise<CadParseSummary> {
  return apiGet<CadParseSummary>(`/api/sheets/${sheetId}/cad-parse`);
}
