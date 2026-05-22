import { apiGet, apiPost } from "./client";

export type DrawingSheet = {
  id: number;
  project_id: number;
  batch_id: number;
  file_id: number;
  page_no: number;
  sheet_type: string;
  drawing_no: string | null;
  drawing_name: string | null;
  discipline: string | null;
  version: string | null;
  issue_date: string | null;
  confidence_score: number | null;
  trust_level: string | null;
  status: string;
  review_status: string;
  thumbnail_path: string | null;
  preview_path: string | null;
  title_crop_path: string | null;
  title_crop_status: string | null;
  title_crop_error_code: string | null;
  title_crop_error_message: string | null;
  cad_preview_path: string | null;
  cad_preview_status: string | null;
  cad_preview_error_code: string | null;
  cad_preview_error_message: string | null;
  cad_preview_url: string | null;
  issue_count: number;
  error_count: number;
  warning_count: number;
  info_count: number;
  thumbnail_url: string | null;
  preview_url: string | null;
  original_file_name: string;
  source_format: string;
  created_at: string;
  updated_at: string;
};

export type PaginatedSheets = {
  items: DrawingSheet[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};

export type SheetQuery = {
  keyword?: string;
  batch_id?: number;
  file_id?: number;
  discipline?: string;
  status?: string;
  review_status?: string;
  trust_level?: string;
  source_format?: string;
  issue_severity?: string;
  issue_code?: string;
  has_issue?: boolean;
  has_error?: boolean;
  has_warning?: boolean;
  low_confidence?: boolean;
  missing_field?: string;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: string;
};

export type BatchSplitResult = {
  batch_id: number;
  file_count: number;
  sheet_count: number;
  failed_count: number;
  files: Array<{
    file_id: number;
    page_count: number;
    sheet_count: number;
    failed_count: number;
  }>;
};

export function splitImportBatch(batchId: number): Promise<BatchSplitResult> {
  return apiPost<BatchSplitResult>(`/api/imports/${batchId}/split`, undefined, {
    timeoutMs: 300_000
  });
}

export function listProjectSheets(
  projectId: number,
  query: SheetQuery = {}
): Promise<PaginatedSheets> {
  const params = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (value !== undefined && value !== "" && value !== null) {
      params.set(key, String(value));
    }
  });
  const queryString = params.toString();
  return apiGet<PaginatedSheets>(
    `/api/projects/${projectId}/sheets${queryString ? `?${queryString}` : ""}`
  );
}

export function getSheet(sheetId: number): Promise<DrawingSheet> {
  return apiGet<DrawingSheet>(`/api/sheets/${sheetId}`);
}
