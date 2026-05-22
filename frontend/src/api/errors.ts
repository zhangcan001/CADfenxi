export class ApiError extends Error {
  status: number;
  errorCode: string | null;

  constructor(status: number, message: string, errorCode: string | null = null) {
    super(message);
    this.status = status;
    this.errorCode = errorCode;
  }
}

export async function readApiError(response: Response): Promise<ApiError> {
  try {
    const payload = (await response.json()) as {
      detail?: string | { error_code?: string; message?: string };
    };
    if (payload.detail && typeof payload.detail === "object") {
      return new ApiError(
        response.status,
        payload.detail.message || `请求失败：${response.status}`,
        payload.detail.error_code ?? null
      );
    }
    if (typeof payload.detail === "string") {
      return new ApiError(response.status, payload.detail);
    }
  } catch {
    // fall through to generic error
  }
  return new ApiError(response.status, `请求失败：${response.status}`);
}
