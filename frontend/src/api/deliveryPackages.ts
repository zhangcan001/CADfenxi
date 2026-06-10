import { apiGet, apiPost } from "./client";

export type DeliveryPackageRequest = {
  include_original_files: boolean;
  include_cad_previews: boolean;
  include_pdf_previews: boolean;
  include_latest_excel: boolean;
};

export type DeliveryPackageResult = {
  package_id: string;
  file_name: string;
  file_size: number;
  download_url: string;
  included: Record<string, boolean>;
  warnings: string[];
};

export function createDeliveryPackage(
  projectId: number,
  payload: DeliveryPackageRequest
): Promise<DeliveryPackageResult> {
  return apiPost<DeliveryPackageResult>(`/api/projects/${projectId}/delivery-package`, payload, {
    timeoutMs: 300_000
  });
}

export async function downloadDeliveryPackage(url: string, fileName: string) {
  const blob = await apiGet<Blob>(url, {
    timeoutMs: 300_000,
    headers: { Accept: "application/zip" },
    responseType: "blob"
  });
  const objectUrl = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = fileName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(objectUrl);
}
