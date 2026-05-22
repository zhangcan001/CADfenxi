import { ApiError, readApiError } from "./errors";

const DEFAULT_TIMEOUT_MS = 60_000;

export interface ApiRequestOptions extends Omit<RequestInit, "signal"> {
  /** Per-request timeout in milliseconds. Defaults to 60s. Pass 0 to disable. */
  timeoutMs?: number;
  /** External AbortSignal — composed with the internal timeout signal. */
  signal?: AbortSignal;
}

export async function apiRequest<T>(url: string, options?: ApiRequestOptions): Promise<T> {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, signal, headers, ...rest } = options ?? {};

  const controller = new AbortController();
  const timer = timeoutMs > 0 ? setTimeout(() => controller.abort(), timeoutMs) : null;
  const onExternalAbort = () => controller.abort(signal?.reason);
  if (signal) {
    if (signal.aborted) {
      controller.abort(signal.reason);
    } else {
      signal.addEventListener("abort", onExternalAbort, { once: true });
    }
  }

  const isFormData = rest.body instanceof FormData;
  const mergedHeaders: Record<string, string> = isFormData
    ? {}
    : { "Content-Type": "application/json" };
  if (headers) {
    new Headers(headers).forEach((value, key) => {
      mergedHeaders[key] = value;
    });
  }

  try {
    const response = await fetch(url, {
      ...rest,
      headers: mergedHeaders,
      signal: controller.signal
    });

    if (!response.ok) {
      throw await readApiError(response);
    }
    if (response.status === 204) {
      return undefined as T;
    }
    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    if (error instanceof DOMException && error.name === "AbortError") {
      if (timer && !signal?.aborted) {
        throw new ApiError(0, `请求超时（${Math.round(timeoutMs / 1000)} 秒）`, "REQUEST_TIMEOUT");
      }
      throw new ApiError(0, "请求已取消", "REQUEST_ABORTED");
    }
    const message = error instanceof Error ? error.message : "网络请求失败";
    throw new ApiError(0, message, "NETWORK_ERROR");
  } finally {
    if (timer) clearTimeout(timer);
    if (signal) signal.removeEventListener("abort", onExternalAbort);
  }
}

export function apiGet<T>(url: string, options?: ApiRequestOptions): Promise<T> {
  return apiRequest<T>(url, options);
}

export function apiPost<T>(url: string, body?: unknown, options?: ApiRequestOptions): Promise<T> {
  return apiRequest<T>(url, {
    ...options,
    method: "POST",
    body: body === undefined ? undefined : body instanceof FormData ? body : JSON.stringify(body)
  });
}

export function apiPatch<T>(url: string, body?: unknown, options?: ApiRequestOptions): Promise<T> {
  return apiRequest<T>(url, {
    ...options,
    method: "PATCH",
    body: body === undefined ? undefined : JSON.stringify(body)
  });
}

export function apiDelete<T>(url: string, options?: ApiRequestOptions): Promise<T> {
  return apiRequest<T>(url, { ...options, method: "DELETE" });
}
