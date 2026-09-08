/** Typed client for the /admin API (all routes under /api/v1/admin). */

const BASE = "/api/v1/admin";

function authHeaders(): HeadersInit {
  const token = localStorage.getItem("bi_token") || "";
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${body.slice(0, 200)}`);
  }
  return res.json() as Promise<T>;
}

export const get = <T,>(path: string) => api<T>(path);
export const post = <T,>(path: string, body?: unknown) =>
  api<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });
export const patch = <T,>(path: string, body: unknown) =>
  api<T>(path, { method: "PATCH", body: JSON.stringify(body) });
export const del = <T,>(path: string) => api<T>(path, { method: "DELETE" });

const ROOT = "/api/v1";

async function rootApi<T>(path: string, init?: RequestInit): Promise<T> {
  const token = localStorage.getItem("bi_token") || "";
  const res = await fetch(`${ROOT}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${body.slice(0, 200)}`);
  }
  return res.json() as Promise<T>;
}

/** Client for non-/admin routers (reports, dashboards, ...). */
export const rget = <T,>(path: string) => rootApi<T>(path);
export const rpost = <T,>(path: string, body?: unknown) =>
  rootApi<T>(path, {
    method: "POST",
    body: body === undefined ? undefined : JSON.stringify(body),
  });
export const rpatch = <T,>(path: string, body: unknown) =>
  rootApi<T>(path, { method: "PATCH", body: JSON.stringify(body) });
export const rdel = <T,>(path: string) => rootApi<T>(path, { method: "DELETE" });

/** Download a binary artifact (reports, audit export) via auth headers. */
export async function download(path: string, filename: string, base: string = BASE) {
  const token = localStorage.getItem("bi_token") || "";
  const res = await fetch(`${base}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
