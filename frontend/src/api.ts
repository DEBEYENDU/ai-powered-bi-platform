/** Typed client for the /admin API (all routes under /api/v1/admin). */

const BASE = "/api/v1/admin";
const ROOT = "/api/v1";

export const TOKEN_KEY = "bi_token";
export const REFRESH_KEY = "bi_refresh_token";

export function authHeaders(): HeadersInit {
  const token = localStorage.getItem(TOKEN_KEY) || "";
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// Single-flight refresh: concurrent 401s share one refresh attempt, and each
// request retries at most once, so an expired session can never loop.
let refreshInFlight: Promise<boolean> | null = null;

async function tryRefresh(): Promise<boolean> {
  const refresh = localStorage.getItem(REFRESH_KEY) || "";
  if (!refresh) return false;
  const res = await fetch(
    `${ROOT}/auth/refresh?token=${encodeURIComponent(refresh)}`,
    { method: "POST" },
  );
  if (!res.ok) return false;
  const data = await res.json().catch(() => ({}));
  if (!data.access_token) return false;
  localStorage.setItem(TOKEN_KEY, data.access_token);
  if (data.refresh_token) localStorage.setItem(REFRESH_KEY, data.refresh_token);
  return true;
}

function redirectToLogin() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
  if (!window.location.pathname.startsWith("/login")) {
    window.location.href = "/login";
  }
}

async function requestJson<T>(url: string, init?: RequestInit, retried = false): Promise<T> {
  let res = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(init?.headers || {}),
    },
  });
  if (res.status === 401 && !retried) {
    if (!refreshInFlight) {
      refreshInFlight = tryRefresh().finally(() => {
        refreshInFlight = null;
      });
    }
    const ok = await refreshInFlight;
    if (!ok) {
      redirectToLogin();
      throw new Error("401 Unauthorized: session expired");
    }
    return requestJson<T>(url, init, true);
  }
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${body.slice(0, 200)}`);
  }
  return res.json() as Promise<T>;
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  return requestJson<T>(`${BASE}${path}`, init);
}

export const get = <T,>(path: string) => api<T>(path);
export const post = <T,>(path: string, body?: unknown) =>
  api<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });
export const patch = <T,>(path: string, body: unknown) =>
  api<T>(path, { method: "PATCH", body: JSON.stringify(body) });
export const del = <T,>(path: string) => api<T>(path, { method: "DELETE" });

/** Client for non-/admin routers (reports, dashboards, ...). */
export const rget = <T,>(path: string) => requestJson<T>(`${ROOT}${path}`);
export const rpost = <T,>(path: string, body?: unknown) =>
  requestJson<T>(`${ROOT}${path}`, {
    method: "POST",
    body: body === undefined ? undefined : JSON.stringify(body),
  });
export const rpatch = <T,>(path: string, body: unknown) =>
  requestJson<T>(`${ROOT}${path}`, { method: "PATCH", body: JSON.stringify(body) });
export const rdel = <T,>(path: string) => requestJson<T>(`${ROOT}${path}`, { method: "DELETE" });

/** Download a binary artifact (reports, audit export) via auth headers. */
export async function download(path: string, filename: string, base: string = BASE) {
  const res = await fetch(`${base}${path}`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
