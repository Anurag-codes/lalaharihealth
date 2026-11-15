"use client";

import { useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { clsx } from "clsx";
import { CalendarClock, HeartPulse, LayoutDashboard, Loader2, LogOut, Stethoscope, UserCircle2 } from "lucide-react";
import { redirectToLogin } from "@/lib/staff/client";
import type { StaffUser } from "@/lib/staff/types";

const NAV = [
  { href: "/staff", label: "Dashboard", icon: LayoutDashboard, exact: true },
  { href: "/staff/appointments", label: "Appointments", icon: CalendarClock, exact: false },
  { href: "/staff/doctors", label: "Doctors", icon: Stethoscope, exact: false },
];

export function StaffShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<StaffUser | null>(null);
  const [loggingOut, setLoggingOut] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/staff/session", { credentials: "same-origin", cache: "no-store", signal: controller.signal })
      .then(async (res) => {
        if (res.status === 401 || res.status === 403) {
          redirectToLogin();
          return;
        }
        if (res.ok) {
          const data = (await res.json()) as { user?: StaffUser };
          if (data.user) setUser(data.user);
        }
      })
      .catch(() => {
        // Network errors surface on the page's own requests.
      });
    return () => controller.abort();
  }, []);

  async function logout() {
    setLoggingOut(true);
    try {
      await fetch("/api/staff/logout", { method: "POST", credentials: "same-origin" });
    } catch {
      // Cookies are cleared server-side; navigate away regardless.
    }
    router.replace("/staff/login");
    router.refresh();
  }

  const displayName = user ? user.full_name?.trim() || user.username : null;

  return (
    <div className="flex min-h-screen flex-col lg:flex-row">
      <a
        href="#staff-main"
        className="sr-only z-50 rounded bg-white px-3 py-2 text-sm font-semibold focus:not-sr-only focus:absolute focus:left-2 focus:top-2"
      >
        Skip to content
      </a>
      <aside className="border-b border-slate-200 bg-white lg:sticky lg:top-0 lg:flex lg:h-screen lg:w-60 lg:shrink-0 lg:flex-col lg:border-b-0 lg:border-r">
        <div className="flex items-center justify-between gap-3 px-4 py-3 lg:px-5 lg:py-5">
          <Link
            href="/staff"
            className="flex items-center gap-2 rounded-lg font-heading text-base font-bold text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          >
            <HeartPulse className="h-6 w-6 text-primary" aria-hidden />
            <span>
              Lalahari <span className="text-primary">Staff</span>
            </span>
          </Link>
          <button
            type="button"
            onClick={logout}
            disabled={loggingOut}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-ink hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-60 lg:hidden"
          >
            {loggingOut ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> : <LogOut className="h-3.5 w-3.5" aria-hidden />}
            Logout
          </button>
        </div>
        <nav aria-label="Staff navigation" className="overflow-x-auto px-2 pb-2 lg:flex-1 lg:px-3">
          <ul className="flex gap-1 lg:flex-col">
            {NAV.map(({ href, label, icon: Icon, exact }) => {
              const active = exact ? pathname === href : pathname === href || pathname.startsWith(`${href}/`);
              return (
                <li key={href}>
                  <Link
                    href={href}
                    aria-current={active ? "page" : undefined}
                    className={clsx(
                      "flex items-center gap-2 whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary",
                      active ? "bg-primary-light text-primary-darker" : "text-slate-600 hover:bg-slate-100 hover:text-ink",
                    )}
                  >
                    <Icon className="h-4 w-4" aria-hidden />
                    {label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
        <div className="hidden border-t border-slate-200 px-5 py-4 lg:block">
          <div className="flex items-center gap-2 text-sm">
            <UserCircle2 className="h-5 w-5 shrink-0 text-slate-400" aria-hidden />
            <div className="min-w-0">
              <p className="truncate font-medium text-ink">{displayName ?? "Signed in"}</p>
              {user && <p className="truncate text-xs text-slate-500">@{user.username}</p>}
            </div>
          </div>
          <button
            type="button"
            onClick={logout}
            disabled={loggingOut}
            className="mt-3 inline-flex w-full items-center justify-center gap-1.5 rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold text-ink hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-60"
          >
            {loggingOut ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <LogOut className="h-4 w-4" aria-hidden />}
            Logout
          </button>
        </div>
      </aside>
      <div className="min-w-0 flex-1">
        {displayName && (
          <p className="border-b border-slate-200 bg-white px-4 py-2 text-xs text-slate-500 lg:hidden">
            Signed in as <span className="font-semibold text-ink">{displayName}</span>
          </p>
        )}
        <main id="staff-main" className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          {children}
        </main>
      </div>
    </div>
  );
}
