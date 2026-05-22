import { readApiError } from "./errors";

export type ImportedFile = {
  id: number;
  original_name: string;
  file_ext: string;
  source_format: string;
  file_size: number;
  file_hash: string;
  page_count: number;
  status: string;
  storage_path: string;
  converted_format: string | null;
  converted_file_path: string | null;
  convert_status: string | null;
  convert_error_code: string | null;
  convert_error_message: string | null;
  warnings: string[];
};

export type DrawingFile = {
  id: number;
  project_id: number;
  batch_id: number;
  original_name: string;
  file_ext: string;
  source_format: string;
  file_size: number;
  file_hash: string;
  page_count: number;
  storage_path: string;
  status: string;
  error_message: string | null;
  parse_status: string | null;
  parse_error_code: string | null;
  parse_error_message: string | null;
  converted_format: string | null;
  converted_file_path: string | null;
  convert_status: string | null;
  convert_error_code: string | null;
  convert_error_message: string | null;
  created_at: string;
  updated_at: string;
};

export type ImportBatch = {
  id: number;
  project_id: number;
  batch_name: string;
  file_count: number;
  sheet_count: number;
  recognized_count: number;
  failed_count: number;
  confirmed_count: number;
  remark: string | null;
  created_at: string;
  updated_at: string;
  files: ImportedFile[];
};

export async function uploadProjectDrawingFiles(
  projectId: number,
  payload: {
    batchName?: string;
    remark?: string;
    files: File[];
  }
): Promise<ImportBatch> {
  const formData = new FormData();
  if (payload.batchName?.trim()) {
    formData.append("batch_name", payload.batchName.trim());
  }
  if (payload.remark?.trim()) {
    formData.append("remark", payload.remark.trim());
  }
  payload.files.forEach((file) => formData.append("files", file));

  const response = await fetch(`/api/projects/${projectId}/imports`, {
    method: "POST",
    body: formData
  });

  if (!response.ok) {
    throw await readApiError(response);
  }

  return response.json() as Promise<ImportBatch>;
}

export const uploadProjectPdfs = uploadProjectDrawingFiles;

export async function listProjectFiles(projectId: number): Promise<DrawingFile[]> {
  const response = await fetch(`/api/projects/${projectId}/files`);
  if (!response.ok) {
    throw await readApiError(response);
  }
  return response.json() as Promise<DrawingFile[]>;
}
