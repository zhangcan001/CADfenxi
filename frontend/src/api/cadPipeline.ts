import { apiGet, apiPost } from "./client";

export type CadPipelineStep =
  | "convert_dwg"
  | "prepare_dxf_sheet"
  | "parse_dxf"
  | "generate_candidates"
  | "fuse_fields"
  | "generate_cad_preview";

export type CadPipelineRequest = {
  steps: CadPipelineStep[];
  skip_completed: boolean;
  continue_on_error: boolean;
};

export type CadPipelineError = {
  file_id: number | null;
  sheet_id: number | null;
  file_name: string | null;
  step: CadPipelineStep;
  error_code: string;
  message: string;
};

export type CadPipelineStepResult = {
  step: CadPipelineStep;
  status: string;
  duration_seconds: number;
  success_count: number;
  failed_count: number;
  skipped_count: number;
  warning_count: number;
  items: Array<{
    file_id: number | null;
    sheet_id: number | null;
    file_name: string | null;
    status: string;
    error_code: string | null;
    message: string | null;
  }>;
  errors: CadPipelineError[];
};

export type CadPipelineResponse = {
  batch_id: number;
  status: string;
  summary: {
    duration_seconds: number;
    start_time: string | null;
    finish_time: string | null;
    total_files: number;
    pdf_files: number;
    dwg_files: number;
    dxf_files: number;
    converted_success: number;
    converted_failed: number;
    sheet_prepared_success: number;
    sheet_prepared_failed: number;
    parse_success: number;
    parse_failed: number;
    candidate_success: number;
    candidate_failed: number;
    fusion_success: number;
    fusion_failed: number;
    cad_preview_success: number;
    cad_preview_failed: number;
    cad_preview_skipped: number;
    cad_preview_warning_count: number;
    skipped_count: number;
    error_count: number;
    warning_count: number;
  };
  steps: CadPipelineStepResult[];
  errors: CadPipelineError[];
};

export type BackgroundJobStatus = {
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
  result_summary: CadPipelineResponse | null;
};

export function startCadPipeline(
  batchId: number,
  payload: CadPipelineRequest
): Promise<BackgroundJobStatus> {
  return apiPost<BackgroundJobStatus>(`/api/imports/${batchId}/cad-pipeline`, payload);
}

export function getCadPipelineJob(
  batchId: number
): Promise<BackgroundJobStatus | null> {
  return apiGet<BackgroundJobStatus | null>(`/api/imports/${batchId}/cad-pipeline/job`);
}
