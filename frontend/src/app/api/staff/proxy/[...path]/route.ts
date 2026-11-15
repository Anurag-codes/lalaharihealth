import { NextResponse, type NextRequest } from "next/server";
import {
  backendUnavailable,
  csrfRejected,
  fetchWithStaffAuth,
  isSameOriginRequest,
  jsonResponse,
  noStore,
  setAuthCookies,
  unauthenticatedResponse,
} from "@/lib/staff/server";

type Ctx = { params: Promise<{ path: string[] }> };

const SEGMENT_RE = /^[A-Za-z0-9_-]+$/;
const MAX_BODY_BYTES = 64 * 1024;
// content-length is not forwarded: fetch transparently decompresses, so it may not match.
const PASSTHROUGH_HEADERS = ["content-type", "content-disposition", "retry-after"];

function isAllowed(method: string, segments: string[]) {
  const path = segments.join("/");
  if (segments[0] === "staff" && segments.length > 1) return method === "GET" || method === "PATCH";
  if (method === "POST") {
    return /^appointments\/\d+\/(assign-doctor|confirm-completion)$/.test(path);
  }
  if (method === "GET") return path === "doctors/specialities";
  return false;
}

function hasUnsafeEncoding(req: NextRequest) {
  const rawPath = new URL(req.url).pathname;
  return /%2f|%5c|%2e|%00/i.test(rawPath) || rawPath.includes("..") || rawPath.includes("//");
}

async function handle(req: NextRequest, ctx: Ctx) {
  const method = req.method.toUpperCase();
  if (method !== "GET" && !isSameOriginRequest(req)) return csrfRejected();

  const { path: segments = [] } = await ctx.params;
  if (
    hasUnsafeEncoding(req) ||
    segments.length === 0 ||
    !segments.every((s) => SEGMENT_RE.test(s)) ||
    !isAllowed(method, segments)
  ) {
    return jsonResponse({ detail: "Not found." }, 404);
  }

  let body: string | undefined;
  if (method !== "GET") {
    body = await req.text();
    if (body.length > MAX_BODY_BYTES) return jsonResponse({ detail: "Request body too large." }, 413);
    if (!body) body = "{}";
  }

  let result;
  try {
    result = await fetchWithStaffAuth(req, `${segments.join("/")}/`, {
      method,
      body,
      search: req.nextUrl.search,
    });
  } catch {
    return backendUnavailable();
  }
  if (result.kind === "unauthenticated") return unauthenticatedResponse(result.clearCookies);

  const { upstream, tokens } = result;
  let res: NextResponse;
  if (upstream.status >= 300 && upstream.status < 400) {
    await upstream.body?.cancel();
    res = jsonResponse({ detail: "Unexpected response from the server." }, 502);
  } else {
    const headers = new Headers();
    for (const name of PASSTHROUGH_HEADERS) {
      const value = upstream.headers.get(name);
      if (value) headers.set(name, value);
    }
    const hasBody = upstream.status !== 204;
    if (!hasBody) await upstream.body?.cancel();
    res = noStore(new NextResponse(hasBody ? upstream.body : null, { status: upstream.status, headers }));
  }
  if (tokens) setAuthCookies(res, tokens);
  return res;
}

export const GET = handle;
export const POST = handle;
export const PATCH = handle;
