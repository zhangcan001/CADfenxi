import { apiGet, apiPost } from "./client";

export type TableExtractionMethod = "acad_table" | "text_cluster";
export type TableKind =
  | "equipment"
  | "material"
  | "drawing_index"
  | "legend"
  | "other";

export type DrawingTableRecord = {
  id: number;
  project_id: number;
  batch_id: number;
  file_id: number;
  sheet_id: number;
  table_index: number;
  extraction_method: TableExtractionMethod;
  table_kind: TableKind;
  layer_name: string | null;
  header: string[];
  rows: string[][];
  row_count: number;
  col_count: number;
  source_bbox: number[] | null;
  warnings: string[];
  created_at: string;
  updated_at: string;
};

export type ExtractTablesRequest = {
  include_acad_table?: boolean;
  include_text_cluster?: boolean;
  force?: boolean;
};

export type ExtractTablesBatchRequest = ExtractTablesRequest & {
  continue_on_error?: boolean;
};

export type ExtractTablesSummary = {
  sheet_id: number;
  acad_table_count: number;
  text_cluster_count: number;
  total_count: number;
  by_kind: Record<string, number>;
};

export type TableJobResultSummary = {
  batch_id: number;
  total_sheets: number;
  success_count: number;
  failed_count: number;
  by_kind: Record<string, number>;
};

export type TableBackgroundJobStatus = {
  id: number;
  job_type: string;
  scope_type: "batch" | "project" | "sheet";
  scope_id: number;
  status: "running" | "completed" | "failed";
  total: number;
  processed: number;
  current_step: string | null;
  message: string | null;
  started_at: string;
  finished_at: string | null;
  result_summary: TableJobResultSummary | null;
};

export function extractTablesForSheet(
  sheetId: number,
  payload?: ExtractTablesRequest
): Promise<ExtractTablesSummary> {
  return apiPost<ExtractTablesSummary>(
    `/api/sheets/${sheetId}/extract-tables`,
    payload ?? {}
  );
}

export function startExtractTablesBatch(
  batchId: number,
  payload?: ExtractTablesBatchRequest
): Promise<TableBackgroundJobStatus> {
  return apiPost<TableBackgroundJobStatus>(
    `/api/imports/${batchId}/extract-tables`,
    payload ?? {}
  );
}

export function getExtractTablesJob(
  batchId: number
): Promise<TableBackgroundJobStatus | null> {
  return apiGet<TableBackgroundJobStatus | null>(
    `/api/imports/${batchId}/extract-tables/job`
  );
}

export function listSheetTables(sheetId: number): Promise<DrawingTableRecord[]> {
  return apiGet<DrawingTableRecord[]>(`/api/sheets/${sheetId}/tables`);
}

export function listProjectTables(
  projectId: number,
  kind?: TableKind
): Promise<DrawingTableRecord[]> {
  const query = kind ? `?kind=${encodeURIComponent(kind)}` : "";
  return apiGet<DrawingTableRecord[]>(`/api/projects/${projectId}/tables${query}`);
}
