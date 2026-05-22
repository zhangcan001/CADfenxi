import { readApiError } from "./errors";

export type CadPipelineStep =
  | "convert_dwg"
  | "prepare_dxf_sheet"
  | "parse_dxf"
  | "generate_candidates"
  | "fuse_fields";

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
    skipped_count: number;
    error_count: number;
    warning_count: number;
  };
  steps: CadPipelineStepResult[];
  errors: CadPipelineError[];
};

export async function runCadPipeline(
  batchId: number,
  payload: CadPipelineRequest
): Promise<CadPipelineResponse> {
  const response = await fetch(`/api/imports/${batchId}/cad-pipeline`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    throw await readApiError(response);
  }
  return response.json() as Promise<CadPipelineResponse>;
}
