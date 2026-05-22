import { apiPost } from "./client";

export type TitleCropBBox = {
  x: number;
  y: number;
  width: number;
  height: number;
};

export type TitleCropResult = {
  sheet_id: number;
  status: string;
  title_crop_path: string | null;
  title_crop_bbox: TitleCropBBox | null;
  error_code: string | null;
  error_message: string | null;
};

export type BatchTitleCropResult = {
  batch_id: number;
  total_count: number;
  success_count: number;
  failed_count: number;
  items: TitleCropResult[];
};

const LONG_OP_TIMEOUT_MS = 300_000;

export function cropSheetTitle(sheetId: number): Promise<TitleCropResult> {
  return apiPost<TitleCropResult>(`/api/sheets/${sheetId}/title-crop`, undefined, {
    timeoutMs: LONG_OP_TIMEOUT_MS
  });
}

export function cropBatchTitles(batchId: number): Promise<BatchTitleCropResult> {
  return apiPost<BatchTitleCropResult>(`/api/imports/${batchId}/title-crops`, undefined, {
    timeoutMs: LONG_OP_TIMEOUT_MS
  });
}
