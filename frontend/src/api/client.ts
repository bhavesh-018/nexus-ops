import type { TokenPair } from "../types/api";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";
const ACCESS_KEY = "nexusops_access_token";
const REFRESH_KEY = "nexusops_refresh_token";

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

export function getStoredTokens(): { access: string | null; refresh: string | null } {
  return {
    access: localStorage.getItem(ACCESS_KEY),
    refresh: localStorage.getItem(REFRESH_KEY)
  };
}

export function saveTokens(pair: TokenPair): void {
  localStorage.setItem(ACCESS_KEY, pair.access_token);
  localStorage.setItem(REFRESH_KEY, pair.refresh_token);
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

async function parseError(resp: Response): Promise<ApiError> {
  try {
    const body = (await resp.json()) as {
      error?: { code?: string; message?: string };
      detail?: string | Array<{ msg?: string }>;
    };
    if (body.error?.message) {
      return new ApiError(resp.status, body.error.code ?? "api_error", body.error.message);
    }
    if (Array.isArray(body.detail) && body.detail[0]?.msg) {
      return new ApiError(resp.status, "validation_error", body.detail[0].msg);
    }
    if (typeof body.detail === "string") {
      return new ApiError(resp.status, "api_error", body.detail);
    }
  } catch {
    // non-JSON response
  }
  return new ApiError(resp.status, "http_error", `Request failed (${resp.status})`);
}

// Single-flight lock: because the backend rotates single-use refresh tokens and treats
// replay as theft, concurrent 401s must share one /auth/refresh call.
let inflightRefresh: Promise<string | null> | null = null;

export async function refreshAccessToken(): Promise<string | null> {
  if (inflightRefresh) {
    return inflightRefresh;
  }
  const { refresh } = getStoredTokens();
  if (!refresh) {
    return null;
  }

  inflightRefresh = (async () => {
    try {
      const resp = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refresh })
      });
      if (!resp.ok) {
        clearTokens();
        return null;
      }
      const pair = (await resp.json()) as TokenPair;
      saveTokens(pair);
      return pair.access_token;
    } catch {
      return null;
    } finally {
      inflightRefresh = null;
    }
  })();

  return inflightRefresh;
}

interface RequestOptions extends RequestInit {
  skipAuth?: boolean;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { skipAuth = false, headers: customHeaders, ...rest } = options;
  const headers = new Headers(customHeaders);
  if (rest.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (!skipAuth) {
    const { access } = getStoredTokens();
    if (access) {
      headers.set("Authorization", `Bearer ${access}`);
    }
  }

  let resp = await fetch(`${API_BASE}${path}`, { ...rest, headers });

  if (resp.status === 401 && !skipAuth) {
    const fresh = await refreshAccessToken();
    if (fresh) {
      headers.set("Authorization", `Bearer ${fresh}`);
      resp = await fetch(`${API_BASE}${path}`, { ...rest, headers });
    }
  }

  if (!resp.ok) {
    throw await parseError(resp);
  }
  if (resp.status === 204) {
    return undefined as T;
  }
  return (await resp.json()) as T;
}
