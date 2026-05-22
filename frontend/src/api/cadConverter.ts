import { apiGet, apiPatch, apiPost } from "./client";

export type ConverterSetting = {
  id: number;
  converter_name: string;
  converter_exe_path: string;
  output_version: string;
  output_type: string;
  is_enabled: boolean;
  last_check_status: string | null;
  last_check_message: string | null;
  created_at: string;
  updated_at: string;
};

export type ConverterSettingPayload = {
  converter_name: string;
  converter_exe_path: string;
  output_version: string;
  output_type: string;
  is_enabled: boolean;
};

export type ConverterCheckResult = {
  setting_id: number;
  status: string;
  message: string;
};

export type DwgConvertResult = {
  file_id: number;
  status: string;
  run_id: number | null;
  converted_file_path: string | null;
  error_code: string | null;
  error_message: string | null;
  warning_code: string | null;
  warning_message: string | null;
};

export type BatchDwgConvertResult = {
  batch_id: number;
  total_count: number;
  success_count: number;
  failed_count: number;
  skipped_count: number;
  items: DwgConvertResult[];
};

export type CadConversionRun = {
  id: number;
  project_id: number;
  batch_id: number;
  source_file_id: number;
  source_format: string;
  target_format: string;
  source_path: string;
  target_path: string | null;
  converter_name: string;
  converter_exe_path: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  error_code: string | null;
  error_message: string | null;
  stdout_log: string | null;
  stderr_log: string | null;
  created_at: string;
};

// DWG -> DXF conversion can take a while (default backend timeout 120s + I/O overhead).
const CONVERT_TIMEOUT_MS = 300_000;

export function getConverterSettings(): Promise<ConverterSetting[]> {
  return apiGet<ConverterSetting[]>("/api/cad/converter-settings");
}

export function saveConverterSettings(
  payload: ConverterSettingPayload,
  settingId?: number
): Promise<ConverterSetting> {
  if (settingId) {
    return apiPatch<ConverterSetting>(`/api/cad/converter-settings/${settingId}`, payload);
  }
  return apiPost<ConverterSetting>("/api/cad/converter-settings", payload);
}

export function checkConverterSetting(settingId: number): Promise<ConverterCheckResult> {
  return apiPost<ConverterCheckResult>(`/api/cad/converter-settings/${settingId}/check`);
}

export function convertDwgFile(fileId: number): Promise<DwgConvertResult> {
  return apiPost<DwgConvertResult>(`/api/files/${fileId}/convert-dwg-to-dxf`, undefined, {
    timeoutMs: CONVERT_TIMEOUT_MS
  });
}

export function convertDwgBatch(batchId: number): Promise<BatchDwgConvertResult> {
  return apiPost<BatchDwgConvertResult>(`/api/imports/${batchId}/convert-dwg-to-dxf`, undefined, {
    timeoutMs: CONVERT_TIMEOUT_MS
  });
}

export function listProjectConversionRuns(projectId: number): Promise<CadConversionRun[]> {
  return apiGet<CadConversionRun[]>(`/api/projects/${projectId}/cad-conversion-runs`);
}

export function listFileConversionRuns(fileId: number): Promise<CadConversionRun[]> {
  return apiGet<CadConversionRun[]>(`/api/files/${fileId}/cad-conversion-runs`);
}
