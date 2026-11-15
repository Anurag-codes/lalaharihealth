import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { StaffShell } from "@/components/staff/StaffShell";
import { ACCESS_COOKIE, REFRESH_COOKIE } from "@/lib/staff/server";

export default async function StaffConsoleLayout({ children }: { children: React.ReactNode }) {
  const cookieStore = await cookies();
  // The refresh cookie is scoped to /api/staff, so on page requests usually only the access
  // cookie is visible; the login page restores the session via the refresh cookie when possible.
  if (!cookieStore.has(ACCESS_COOKIE) && !cookieStore.has(REFRESH_COOKIE)) {
    redirect("/staff/login");
  }
  return <StaffShell>{children}</StaffShell>;
}
