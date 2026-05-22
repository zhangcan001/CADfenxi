import { apiGet, apiPost } from "./client";

export type ExportCheckResult = {
  can_export: boolean;
  is_complete_ledger: boolean;
  summary_message: string;
  sheet_count: number;
  unconfirmed_count: number;
  open_error_count: number;
  open_warning_count: number;
  open_error_sheet_count: number;
  open_warning_sheet_count: number;
  failed_count: number;
  empty_drawing_no_count: number;
  empty_drawing_name_count: number;
  empty_discipline_count: number;
  trust_level_d_count: number;
  duplicate_drawing_no_count: number;
  warning_count: number;
  warnings: string[];
};

export type ExportExcelResult = {
  export_id: number;
  project_id: number;
  file_name: string;
  file_path: string;
  sheet_count: number;
  ledger_row_count: number;
  issue_row_count: number;
  issue_count: number;
  warning_count: number;
  summary_sheet_count: number;
  precheck: {
    total_sheets: number;
    unreviewed_count: number;
    missing_drawing_no_count: number;
    missing_drawing_name_count: number;
    open_error_count: number;
    open_warning_count: number;
    d_level_count: number;
  };
  include_unconfirmed: boolean;
  has_open_errors: boolean;
  created_at: string;
  download_url: string;
  warning_summary: ExportCheckResult;
};

export type ExportRecord = {
  export_id: number;
  export_type: string;
  file_name: string;
  sheet_count: number;
  issue_count: number;
  include_unconfirmed: boolean;
  has_open_errors: boolean;
  created_at: string;
  download_url: string;
};

export function checkExport(projectId: number): Promise<ExportCheckResult> {
  return apiPost<ExportCheckResult>(`/api/projects/${projectId}/exports/check`);
}

export function exportExcel(
  projectId: number,
  payload: { confirm_incomplete: boolean; include_issues?: boolean; filter?: unknown }
): Promise<ExportExcelResult> {
  return apiPost<ExportExcelResult>(`/api/projects/${projectId}/exports/excel`, payload, {
    timeoutMs: 300_000
  });
}

export function listExports(projectId: number): Promise<ExportRecord[]> {
  return apiGet<ExportRecord[]>(`/api/projects/${projectId}/exports`);
}

export function downloadExport(exportId: number) {
  window.location.href = `/api/exports/${exportId}/download`;
}
