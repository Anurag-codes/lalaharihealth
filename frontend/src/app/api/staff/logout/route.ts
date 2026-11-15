import type { NextRequest } from "next/server";
import {
  ACCESS_COOKIE,
  REFRESH_COOKIE,
  callBackend,
  clearAuthCookies,
  csrfRejected,
  isSameOriginRequest,
  noStore,
} from "@/lib/staff/server";
import { NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  if (!isSameOriginRequest(req)) return csrfRejected();

  const access = req.cookies.get(ACCESS_COOKIE)?.value;
  const refresh = req.cookies.get(REFRESH_COOKIE)?.value;
  if (refresh) {
    try {
      const upstream = await callBackend(req, "auth/staff/logout/", {
        method: "POST",
        body: JSON.stringify({ refresh }),
        access,
      });
      await upstream.body?.cancel();
    } catch {
      // Best effort: cookies are cleared regardless.
    }
  }

  const res = noStore(new NextResponse(null, { status: 204 }));
  clearAuthCookies(res);
  return res;
}
