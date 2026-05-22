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

export async function prepareDxfSheet(fileId: number): Promise<DxfSheetPrepareResult> {
  const response = await fetch(`/api/files/${fileId}/prepare-dxf-sheet`, {
    method: "POST"
  });
  if (!response.ok) {
    throw await readApiError(response);
  }
  return response.json() as Promise<DxfSheetPrepareResult>;
}

export async function prepareDxfSheetsForBatch(
  batchId: number
): Promise<BatchDxfSheetPrepareResult> {
  const response = await fetch(`/api/imports/${batchId}/prepare-dxf-sheets`, {
    method: "POST"
  });
  if (!response.ok) {
    throw await readApiError(response);
  }
  return response.json() as Promise<BatchDxfSheetPrepareResult>;
}

export async function parseDxfFile(fileId: number): Promise<CadParseResult> {
  const response = await fetch(`/api/files/${fileId}/parse-dxf`, {
    method: "POST"
  });
  if (!response.ok) {
    throw await readApiError(response);
  }
  return response.json() as Promise<CadParseResult>;
}

export async function parseDxfBatch(batchId: number): Promise<BatchCadParseResult> {
  const response = await fetch(`/api/imports/${batchId}/parse-dxf`, {
    method: "POST"
  });
  if (!response.ok) {
    throw await readApiError(response);
  }
  return response.json() as Promise<BatchCadParseResult>;
}

export async function getCadParseSummary(sheetId: number): Promise<CadParseSummary> {
  const response = await fetch(`/api/sheets/${sheetId}/cad-parse`);
  if (!response.ok) {
    throw await readApiError(response);
  }
  return response.json() as Promise<CadParseSummary>;
}
import { readApiError } from "./errors";
