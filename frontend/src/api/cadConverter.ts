import { readApiError } from "./errors";

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

export async function getConverterSettings(): Promise<ConverterSetting[]> {
  const response = await fetch("/api/cad/converter-settings");
  if (!response.ok) {
    throw await readApiError(response);
  }
  return response.json() as Promise<ConverterSetting[]>;
}

export async function saveConverterSettings(
  payload: ConverterSettingPayload,
  settingId?: number
): Promise<ConverterSetting> {
  const response = await fetch(
    settingId ? `/api/cad/converter-settings/${settingId}` : "/api/cad/converter-settings",
    {
      method: settingId ? "PATCH" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }
  );
  if (!response.ok) {
    throw await readApiError(response);
  }
  return response.json() as Promise<ConverterSetting>;
}

export async function checkConverterSetting(settingId: number): Promise<ConverterCheckResult> {
  const response = await fetch(`/api/cad/converter-settings/${settingId}/check`, {
    method: "POST"
  });
  if (!response.ok) {
    throw await readApiError(response);
  }
  return response.json() as Promise<ConverterCheckResult>;
}

export async function convertDwgFile(fileId: number): Promise<DwgConvertResult> {
  const response = await fetch(`/api/files/${fileId}/convert-dwg-to-dxf`, {
    method: "POST"
  });
  if (!response.ok) {
    throw await readApiError(response);
  }
  return response.json() as Promise<DwgConvertResult>;
}

export async function convertDwgBatch(batchId: number): Promise<BatchDwgConvertResult> {
  const response = await fetch(`/api/imports/${batchId}/convert-dwg-to-dxf`, {
    method: "POST"
  });
  if (!response.ok) {
    throw await readApiError(response);
  }
  return response.json() as Promise<BatchDwgConvertResult>;
}

export async function listProjectConversionRuns(projectId: number): Promise<CadConversionRun[]> {
  const response = await fetch(`/api/projects/${projectId}/cad-conversion-runs`);
  if (!response.ok) {
    throw await readApiError(response);
  }
  return response.json() as Promise<CadConversionRun[]>;
}

export async function listFileConversionRuns(fileId: number): Promise<CadConversionRun[]> {
  const response = await fetch(`/api/files/${fileId}/cad-conversion-runs`);
  if (!response.ok) {
    throw await readApiError(response);
  }
  return response.json() as Promise<CadConversionRun[]>;
}
