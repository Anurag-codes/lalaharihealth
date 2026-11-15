import type { NextRequest } from "next/server";
import {
  backendUnavailable,
  callBackend,
  clientIp,
  consumeLoginAttempt,
  csrfRejected,
  isSameOriginRequest,
  jsonResponse,
  readJsonSafe,
  setAuthCookies,
} from "@/lib/staff/server";

export async function POST(req: NextRequest) {
  if (!isSameOriginRequest(req)) return csrfRejected();

  const limit = consumeLoginAttempt(clientIp(req));
  if (!limit.allowed) {
    const res = jsonResponse(
      { detail: "Too many login attempts. Please wait a few minutes and try again." },
      429,
    );
    res.headers.set("Retry-After", String(limit.retryAfter));
    return res;
  }

  let payload: unknown;
  try {
    payload = await req.json();
  } catch {
    return jsonResponse({ detail: "Invalid request body." }, 400);
  }
  const { username, password } = (payload ?? {}) as { username?: unknown; password?: unknown };
  if (typeof username !== "string" || typeof password !== "string" || !username.trim() || !password) {
    return jsonResponse({ detail: "Username and password are required." }, 400);
  }
  if (username.length > 150 || password.length > 512) {
    return jsonResponse({ detail: "Invalid username or password." }, 400);
  }

  let upstream: Response;
  try {
    upstream = await callBackend(req, "auth/staff/login/", {
      method: "POST",
      body: JSON.stringify({ username: username.trim(), password }),
    });
  } catch {
    return backendUnavailable();
  }

  const data = await readJsonSafe(upstream);
  if (!upstream.ok) {
    const res = jsonResponse(data ?? { detail: "Login failed. Please try again." }, upstream.status);
    const retryAfter = upstream.headers.get("retry-after");
    if (retryAfter) res.headers.set("Retry-After", retryAfter);
    return res;
  }

  const { access, refresh, user } = (data ?? {}) as { access?: unknown; refresh?: unknown; user?: unknown };
  if (typeof access !== "string" || typeof refresh !== "string" || !user) {
    return jsonResponse({ detail: "Unexpected response from the server." }, 502);
  }

  const res = jsonResponse({ user });
  setAuthCookies(res, { access, refresh });
  return res;
}
