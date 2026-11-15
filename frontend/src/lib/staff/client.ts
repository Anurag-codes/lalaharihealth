"use client";

import { useCallback, useEffect, useState } from "react";

const FIELD_LABELS: Record<string, string> = {
  doctor_id: "Doctor",
  starts_at: "Date & time",
  patient_name: "Patient name",
  patient_age: "Age",
  patient_gender: "Gender",
  username: "Username",
  password: "Password",
};

function fieldLabel(key: string) {
  if (FIELD_LABELS[key]) return FIELD_LABELS[key];
  const text = key.replace(/_/g, " ").trim();
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/** Flattens DRF error payloads ({detail}, {field: [msg]}, [msg], {field: msg}, nested) into readable lines. */
export function flattenApiErrors(data: unknown, prefix = ""): string[] {
  if (data === null || data === undefined || data === "") return [];
  if (typeof data === "string" || typeof data === "number" || typeof data === "boolean") {
    return [prefix ? `${prefix}: ${String(data)}` : String(data)];
  }
  if (Array.isArray(data)) return data.flatMap((item) => flattenApiErrors(item, prefix));
  if (typeof data === "object") {
    return Object.entries(data as Record<string, unknown>).flatMap(([key, value]) => {
      const isGeneral = key === "detail" || key === "non_field_errors" || key === "message";
      const label = isGeneral ? prefix : prefix ? `${prefix} › ${fieldLabel(key)}` : fieldLabel(key);
      return flattenApiErrors(value, label);
    });
  }
  return [];
}

export class StaffApiError extends Error {
  status: number;
  data: unknown;
  messages: string[];

  constructor(status: number, data: unknown, fallback: string) {
    const messages = flattenApiErrors(data);
    const list = messages.length ? messages : [fallback];
    super(list.join(" "));
    this.status = status;
    this.data = data;
    this.messages = list;
  }
}

export function errorMessages(error: unknown): string[] {
  if (error instanceof StaffApiError) return error.messages;
  if (error instanceof Error && error.message) return [error.message];
  return ["Something went wrong. Please try again."];
}

let redirecting = false;

export function redirectToLogin() {
  if (typeof window === "undefined" || redirecting) return;
  redirecting = true;
  const next = `${window.location.pathname}${window.location.search}`;
  window.location.replace(`/staff/login?next=${encodeURIComponent(next)}`);
}

export function withQuery(path: string, params: Record<string, string | number | null | undefined>) {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== "") search.set(key, String(value));
  }
  const qs = search.toString();
  return qs ? `${path}?${qs}` : path;
}

/** Path within the backend API (e.g. "staff/summary") → same-origin BFF proxy URL. */
export function proxyUrl(path: string) {
  const [pathname, query] = path.split("?", 2);
  const clean = pathname.replace(/^\/+|\/+$/g, "");
  return `/api/staff/proxy/${clean}${query ? `?${query}` : ""}`;
}

/** Maps a backend download path like "/api/v1/staff/…/download/" to the proxy URL, or null. */
export function proxyDownloadUrl(downloadPath: string | null | undefined) {
  if (!downloadPath) return null;
  let pathname = downloadPath;
  try {
    pathname = new URL(downloadPath, "http://local").pathname;
  } catch {
    return null;
  }
  if (!pathname.startsWith("/api/v1/staff/")) return null;
  return proxyUrl(pathname.slice("/api/v1/".length));
}

export async function staffFetch<T>(
  path: string,
  init: { method?: "GET" | "POST" | "PATCH"; body?: unknown; signal?: AbortSignal } = {},
): Promise<T> {
  const method = init.method ?? "GET";
  let res: Response;
  try {
    res = await fetch(proxyUrl(path), {
      method,
      headers: method === "GET" ? { Accept: "application/json" } : { Accept: "application/json", "Content-Type": "application/json" },
      body: method === "GET" ? undefined : JSON.stringify(init.body ?? {}),
      credentials: "same-origin",
      cache: "no-store",
      signal: init.signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    throw new StaffApiError(0, null, "Network error. Check your connection and try again.");
  }

  if (res.status === 401) {
    redirectToLogin();
    throw new StaffApiError(401, null, "Your session has expired. Please sign in again.");
  }
  if (res.status === 204) return undefined as T;

  const text = await res.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = null;
    }
  }
  if (!res.ok) {
    const fallback =
      res.status === 403
        ? "You don't have permission to do that."
        : res.status === 404
          ? "Not found."
          : res.status === 429
            ? "Too many requests. Please wait and try again."
            : `Request failed (${res.status}).`;
    throw new StaffApiError(res.status, data, fallback);
  }
  return data as T;
}

/**
 * Loads a staff API resource whenever `path` changes. Keeps the previous data while
 * reloading so tables don't flash empty.
 */
export function useStaffResource<T>(path: string | null) {
  const [reloadToken, setReloadToken] = useState(0);
  const [state, setState] = useState<{ key: string | null; data?: T; error?: unknown }>({ key: null });
  const key = path === null ? null : `${path}#${reloadToken}`;

  useEffect(() => {
    if (path === null || key === null) return;
    const controller = new AbortController();
    staffFetch<T>(path, { signal: controller.signal }).then(
      (data) => setState({ key, data }),
      (error) => {
        if (!controller.signal.aborted) setState((prev) => ({ key, data: prev.data, error }));
      },
    );
    return () => controller.abort();
  }, [path, key]);

  const reload = useCallback(() => setReloadToken((t) => t + 1), []);
  const setData = useCallback(
    (data: T) => setState({ key, data }),
    [key],
  );

  return {
    data: state.data,
    error: state.key === key ? state.error : undefined,
    loading: key !== null && state.key !== key,
    reload,
    setData,
  };
}

export function normalizeList<T>(data: T[] | { results?: T[] } | null | undefined): T[] {
  if (!data) return [];
  if (Array.isArray(data)) return data;
  return Array.isArray(data.results) ? data.results : [];
}
