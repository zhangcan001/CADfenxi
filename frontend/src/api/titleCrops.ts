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

export async function cropSheetTitle(sheetId: number): Promise<TitleCropResult> {
  const response = await fetch(`/api/sheets/${sheetId}/title-crop`, {
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Title crop failed: ${response.status}`);
  }
  return response.json() as Promise<TitleCropResult>;
}

export async function cropBatchTitles(batchId: number): Promise<BatchTitleCropResult> {
  const response = await fetch(`/api/imports/${batchId}/title-crops`, {
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Batch title crop failed: ${response.status}`);
  }
  return response.json() as Promise<BatchTitleCropResult>;
}
