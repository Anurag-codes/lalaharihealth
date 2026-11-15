// Server-only helpers for the staff BFF route handlers. Never import from client components.
import { NextResponse, type NextRequest } from "next/server";
import { API_BASE_URL } from "@/lib/api";

export const ACCESS_COOKIE = "lh_staff_access";
export const REFRESH_COOKIE = "lh_staff_refresh";
export const REFRESH_COOKIE_PATH = "/api/staff";
const ACCESS_MAX_AGE = 60 * 60;
const REFRESH_MAX_AGE = 7 * 24 * 60 * 60;
const BACKEND_TIMEOUT_MS = 20_000;

export type StaffTokens = { access: string; refresh: string };

export function backendBase() {
  return process.env.API_INTERNAL_BASE_URL?.trim().replace(/\/+$/, "") || API_BASE_URL;
}

export function backendUrl(path: string, search = "") {
  return `${backendBase()}/api/v1/${path.replace(/^\/+/, "")}${search}`;
}

function cookieBase() {
  return {
    httpOnly: true,
    sameSite: "strict" as const,
    secure: process.env.NODE_ENV === "production",
  };
}

export function setAuthCookies(res: NextResponse, tokens: StaffTokens) {
  res.cookies.set(ACCESS_COOKIE, tokens.access, { ...cookieBase(), path: "/", maxAge: ACCESS_MAX_AGE });
  res.cookies.set(REFRESH_COOKIE, tokens.refresh, {
    ...cookieBase(),
    path: REFRESH_COOKIE_PATH,
    maxAge: REFRESH_MAX_AGE,
  });
}

export function clearAuthCookies(res: NextResponse) {
  res.cookies.set(ACCESS_COOKIE, "", { ...cookieBase(), path: "/", maxAge: 0 });
  res.cookies.set(REFRESH_COOKIE, "", { ...cookieBase(), path: REFRESH_COOKIE_PATH, maxAge: 0 });
}

export function noStore<T extends Response>(res: T): T {
  res.headers.set("Cache-Control", "no-store");
  res.headers.set("X-Content-Type-Options", "nosniff");
  return res;
}

export function jsonResponse(body: unknown, status = 200) {
  return noStore(NextResponse.json(body, { status }));
}

export function clientIp(req: NextRequest) {
  const realIp = req.headers.get("x-real-ip")?.trim();
  if (realIp) return realIp;
  const forwarded = req.headers.get("x-forwarded-for")?.split(",")[0]?.trim();
  return forwarded || "unknown";
}

/** Headers that let the backend attribute requests (and throttles) to the real client. */
function forwardedHeaders(req: NextRequest): Record<string, string> {
  const headers: Record<string, string> = {};
  const ip = clientIp(req);
  if (ip !== "unknown") headers["X-Forwarded-For"] = ip;
  const ua = req.headers.get("user-agent");
  if (ua) headers["User-Agent"] = ua.slice(0, 512);
  return headers;
}

/**
 * CSRF defence for state-changing requests: the browser-supplied Origin must match this
 * site's own origin (or the browser must flag the request as same-origin).
 */
export function isSameOriginRequest(req: NextRequest) {
  if (req.headers.get("sec-fetch-site") === "same-origin") return true;
  const origin = req.headers.get("origin");
  if (!origin || origin === "null") return false;

  const allowed = new Set<string>([req.nextUrl.origin]);
  const host = req.headers.get("x-forwarded-host")?.split(",")[0]?.trim() || req.headers.get("host");
  if (host) {
    const proto =
      req.headers.get("x-forwarded-proto")?.split(",")[0]?.trim() || req.nextUrl.protocol.replace(/:$/, "");
    allowed.add(`${proto}://${host}`);
  }
  return allowed.has(origin);
}

export function csrfRejected() {
  return jsonResponse({ detail: "Cross-site request blocked." }, 403);
}

// ---- Login rate limiting (in-memory, per server instance) ----
const LOGIN_WINDOW_MS = 15 * 60 * 1000;
const LOGIN_MAX_ATTEMPTS = 20;
const loginAttempts = new Map<string, { count: number; resetAt: number }>();

export function consumeLoginAttempt(ip: string) {
  const now = Date.now();
  if (loginAttempts.size > 5000) {
    for (const [key, entry] of loginAttempts) {
      if (entry.resetAt <= now) loginAttempts.delete(key);
    }
  }
  const entry = loginAttempts.get(ip);
  if (!entry || entry.resetAt <= now) {
    loginAttempts.set(ip, { count: 1, resetAt: now + LOGIN_WINDOW_MS });
    return { allowed: true, retryAfter: 0 };
  }
  entry.count += 1;
  if (entry.count > LOGIN_MAX_ATTEMPTS) {
    return { allowed: false, retryAfter: Math.ceil((entry.resetAt - now) / 1000) };
  }
  return { allowed: true, retryAfter: 0 };
}

// ---- Backend calls ----
export async function callBackend(
  req: NextRequest,
  path: string,
  init: { method?: string; body?: string; search?: string; access?: string } = {},
) {
  const headers: Record<string, string> = { Accept: "application/json, */*", ...forwardedHeaders(req) };
  if (init.body !== undefined) headers["Content-Type"] = "application/json";
  if (init.access) headers.Authorization = `Bearer ${init.access}`;
  return fetch(backendUrl(path, init.search ?? ""), {
    method: init.method ?? "GET",
    headers,
    body: init.body,
    cache: "no-store",
    redirect: "manual",
    signal: AbortSignal.timeout(BACKEND_TIMEOUT_MS),
  });
}

/*
 * Refresh tokens rotate, so concurrent requests holding the same (old) refresh token must
 * share one refresh call; otherwise the second call would fail and log the user out.
 */
const refreshCache = new Map<string, { promise: Promise<StaffTokens | null>; expiresAt: number }>();
const REFRESH_REUSE_MS = 60_000;

async function doRefresh(req: NextRequest, refresh: string): Promise<StaffTokens | null> {
  try {
    const res = await callBackend(req, "auth/token/refresh/", {
      method: "POST",
      body: JSON.stringify({ refresh }),
    });
    if (!res.ok) {
      await res.body?.cancel();
      return null;
    }
    const data = (await res.json()) as { access?: unknown; refresh?: unknown };
    if (typeof data.access !== "string" || !data.access) return null;
    return {
      access: data.access,
      refresh: typeof data.refresh === "string" && data.refresh ? data.refresh : refresh,
    };
  } catch {
    return null;
  }
}

export function refreshTokens(req: NextRequest, refresh: string) {
  const now = Date.now();
  for (const [key, entry] of refreshCache) {
    if (entry.expiresAt <= now) refreshCache.delete(key);
  }
  const cached = refreshCache.get(refresh);
  if (cached) return cached.promise;
  const promise = doRefresh(req, refresh);
  refreshCache.set(refresh, { promise, expiresAt: now + REFRESH_REUSE_MS });
  void promise.then((tokens) => {
    if (!tokens) refreshCache.delete(refresh);
  });
  return promise;
}

export type AuthedResult =
  | { kind: "ok"; upstream: Response; tokens: StaffTokens | null }
  | { kind: "unauthenticated"; clearCookies: boolean };

/** Calls the backend with the staff access token, refreshing (once) on 401 / missing access. */
export async function fetchWithStaffAuth(
  req: NextRequest,
  path: string,
  init: { method?: string; body?: string; search?: string } = {},
): Promise<AuthedResult> {
  let access = req.cookies.get(ACCESS_COOKIE)?.value;
  const refresh = req.cookies.get(REFRESH_COOKIE)?.value;
  let tokens: StaffTokens | null = null;

  if (!access) {
    if (!refresh) return { kind: "unauthenticated", clearCookies: false };
    tokens = await refreshTokens(req, refresh);
    if (!tokens) return { kind: "unauthenticated", clearCookies: true };
    access = tokens.access;
  }

  let upstream = await callBackend(req, path, { ...init, access });
  if (upstream.status === 401) {
    await upstream.body?.cancel();
    if (tokens || !refresh) return { kind: "unauthenticated", clearCookies: true };
    tokens = await refreshTokens(req, refresh);
    if (!tokens) return { kind: "unauthenticated", clearCookies: true };
    upstream = await callBackend(req, path, { ...init, access: tokens.access });
    if (upstream.status === 401) {
      await upstream.body?.cancel();
      return { kind: "unauthenticated", clearCookies: true };
    }
  }
  return { kind: "ok", upstream, tokens };
}

export function unauthenticatedResponse(clearCookies: boolean) {
  const res = jsonResponse({ detail: "Authentication required." }, 401);
  if (clearCookies) clearAuthCookies(res);
  return res;
}

export function backendUnavailable() {
  return jsonResponse({ detail: "Could not reach the server. Please try again." }, 502);
}

export async function readJsonSafe(res: Response): Promise<unknown> {
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}
