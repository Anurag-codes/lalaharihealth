import type { NextRequest } from "next/server";
import {
  backendUnavailable,
  fetchWithStaffAuth,
  jsonResponse,
  readJsonSafe,
  setAuthCookies,
  unauthenticatedResponse,
} from "@/lib/staff/server";

export async function GET(req: NextRequest) {
  let result;
  try {
    result = await fetchWithStaffAuth(req, "staff/me/");
  } catch {
    return backendUnavailable();
  }
  if (result.kind === "unauthenticated") return unauthenticatedResponse(result.clearCookies);

  const { upstream, tokens } = result;
  const data = await readJsonSafe(upstream);
  const res = upstream.ok
    ? jsonResponse({ user: data })
    : jsonResponse(data ?? { detail: "Could not load your session." }, upstream.status);
  if (tokens) setAuthCookies(res, tokens);
  return res;
}
