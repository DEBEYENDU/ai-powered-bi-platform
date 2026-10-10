/** Typed client for the /admin API (all routes under /api/v1/admin). */

const BASE = "/api/v1/admin";
const ROOT = "/api/v1";

export const TOKEN_KEY = "bi_token";
export const REFRESH_KEY = "bi_refresh_token";

/* ------------------------------------------------------------------ */
/* Shared session state                                                */
/* ------------------------------------------------------------------ */

export type AuthStatus = "unknown" | "authenticated" | "unauthenticated";

function readExpiry(token: string): number | null {
  try {
    const payload = token.split(".")[1];
    if (!payload) return null;
    const json = JSON.parse(atob(payload.replace(/-/g, "+").replace(/_/g, "/")));
    return typeof json.exp === "number" ? json.exp * 1000 : null;
  } catch {
    return null;
  }
}

function initialStatus(): AuthStatus {
  const token = localStorage.getItem(TOKEN_KEY);
  if (!token) return "unauthenticated";
  const exp = readExpiry(token);
  // Unknown expiry: treat as usable; the 401 -> refresh path will correct it.
  if (exp === null) return "authenticated";
  return exp > Date.now() + 5_000 ? "authenticated" : "unknown";
}

let authStatus: AuthStatus | null = null;
const authListeners = new Set<(s: AuthStatus) => void>();

/** Lazy: read localStorage on first use so a token set before first render is seen. */
function currentStatus(): AuthStatus {
  if (authStatus === null) authStatus = initialStatus();
  return authStatus;
}

function setAuthStatus(next: AuthStatus) {
  if (currentStatus() === next) return;
  authStatus = next;
  authListeners.forEach((fn) => fn(next));
}

export function getAuthStatus(): AuthStatus {
  return currentStatus();
}

export function onAuthChange(fn: (s: AuthStatus) => void): () => void {
  authListeners.add(fn);
  return () => authListeners.delete(fn);
}

/** Persist a fresh token pair and mark the session authenticated. */
export function setSession(access: string, refresh?: string) {
  localStorage.setItem(TOKEN_KEY, access);
  if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
  setAuthStatus("authenticated");
}

/** Drop every trace of the session and mark it unauthenticated. */
export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
  setAuthStatus("unauthenticated");
}

export function authHeaders(): HeadersInit {
  const token = localStorage.getItem(TOKEN_KEY) || "";
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// Single-flight refresh: concurrent 401s share one refresh attempt, and each
// request retries at most once, so an expired session can never loop.
let refreshInFlight: Promise<boolean> | null = null;

export async function refreshSession(): Promise<boolean> {
  if (!refreshInFlight) {
    refreshInFlight = tryRefresh().finally(() => {
      refreshInFlight = null;
    });
  }
  const ok = await refreshInFlight;
  setAuthStatus(ok ? "authenticated" : "unauthenticated");
  return ok;
}

async function tryRefresh(): Promise<boolean> {
  const refresh = localStorage.getItem(REFRESH_KEY) || "";
  if (!refresh) return false;
  try {
    const res = await fetch(`${ROOT}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token: refresh }),
    });
    if (!res.ok) return false;
    const data = await res.json().catch(() => ({}));
    if (!data.access_token) return false;
    localStorage.setItem(TOKEN_KEY, data.access_token);
    if (data.refresh_token) localStorage.setItem(REFRESH_KEY, data.refresh_token);
    return true;
  } catch {
    return false;
  }
}

/**
 * Validate the stored session once at startup: an expired access token is
 * refreshed with the refresh token before any protected page renders. An
 * invalid refresh token clears the session so the user lands on /login.
 */
export function ensureValidSession(): Promise<AuthStatus> {
  const status = currentStatus();
  if (status !== "unknown") return Promise.resolve(status);
  return refreshSession().then(() => currentStatus());
}

function redirectToLogin() {
  clearSession();
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
    const ok = await refreshSession();
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

/**
 * fetch() with the Authorization header plus the same single-shot 401 ->
 * refresh -> retry behaviour as requestJson. Used by streaming endpoints
 * (AI chat SSE) that cannot go through requestJson.
 */
export async function fetchWithAuth(
  url: string,
  init: RequestInit = {},
  retried = false,
): Promise<Response> {
  const headers: Record<string, string> = {
    ...(authHeaders() as Record<string, string>),
    ...((init.headers as Record<string, string>) || {}),
  };
  const res = await fetch(url, { ...init, headers });
  if (res.status === 401 && !retried) {
    const ok = await refreshSession();
    if (!ok) {
      redirectToLogin();
      throw new Error("401 Unauthorized: session expired");
    }
    return fetchWithAuth(url, init, true);
  }
  return res;
}
