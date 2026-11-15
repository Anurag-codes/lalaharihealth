"use client";

import Link from "next/link";
import { clsx } from "clsx";
import { AlertTriangle, ArrowRight, CalendarCheck2, CalendarDays, CheckCheck, CreditCard, RefreshCw, UserRoundSearch } from "lucide-react";
import { useStaffResource } from "@/lib/staff/client";
import type { AppointmentItem, Paginated, StaffSummary } from "@/lib/staff/types";
import { formatDate } from "@/lib/staff/time";
import { AppointmentsTable } from "@/components/staff/AppointmentsTable";
import { Card, ErrorAlert, Spinner, btnClasses } from "@/components/staff/ui";

const CARDS = [
  { key: "needs_doctor", queue: "needs_doctor", label: "Needs a doctor", icon: UserRoundSearch, tone: "orange" },
  { key: "overdue", queue: "overdue", label: "Overdue", icon: AlertTriangle, tone: "rose" },
  { key: "today_count", queue: "today", label: "Today", icon: CalendarDays, tone: "teal" },
  { key: "awaiting_payment", queue: "awaiting_payment", label: "Awaiting payment", icon: CreditCard, tone: "amber" },
  { key: "completion_pending", queue: "completion_pending", label: "Completion pending", icon: CheckCheck, tone: "sky" },
  { key: "upcoming_confirmed", queue: "upcoming", label: "Upcoming confirmed", icon: CalendarCheck2, tone: "emerald" },
] as const;

const TONES: Record<string, string> = {
  orange: "bg-orange-50 text-orange-700",
  rose: "bg-rose-50 text-rose-700",
  teal: "bg-primary-light text-primary-darker",
  amber: "bg-amber-50 text-amber-700",
  sky: "bg-sky-50 text-sky-700",
  emerald: "bg-emerald-50 text-emerald-700",
};

export function DashboardView() {
  const summary = useStaffResource<StaffSummary>("staff/summary");
  const needsDoctor = useStaffResource<Paginated<AppointmentItem>>("staff/appointments?queue=needs_doctor&ordering=slot_time");
  const today = useStaffResource<Paginated<AppointmentItem>>("staff/appointments?queue=today&ordering=slot_time");

  function refreshAll() {
    summary.reload();
    needsDoctor.reload();
    today.reload();
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-heading text-2xl font-bold text-ink">Dashboard</h1>
          <p className="text-sm text-slate-500">
            {summary.data?.today_date ? `Today is ${formatDate(summary.data.today_date)} (India time)` : "Operations overview"}
          </p>
        </div>
        <button type="button" onClick={refreshAll} className={btnClasses("secondary", "sm")}>
          <RefreshCw className={clsx("h-4 w-4", (summary.loading || needsDoctor.loading || today.loading) && "animate-spin")} aria-hidden />
          Refresh
        </button>
      </div>

      {Boolean(summary.error) && <ErrorAlert error={summary.error} title="Couldn't load the summary" />}

      <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3" aria-busy={summary.loading}>
        {CARDS.map(({ key, queue, label, icon: Icon, tone }) => {
          const value = summary.data ? summary.data[key] : null;
          return (
            <li key={key}>
              <Link
                href={`/staff/appointments?queue=${queue}`}
                className="group flex items-center gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-primary/50 hover:shadow focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
              >
                <span className={clsx("flex h-11 w-11 shrink-0 items-center justify-center rounded-lg", TONES[tone])}>
                  <Icon className="h-5 w-5" aria-hidden />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block text-sm font-medium text-slate-600">{label}</span>
                  <span className="block font-heading text-2xl font-bold text-ink">
                    {value ?? (summary.loading ? "…" : "—")}
                  </span>
                </span>
                <ArrowRight className="h-4 w-4 text-slate-400 transition group-hover:translate-x-0.5 group-hover:text-primary" aria-hidden />
              </Link>
            </li>
          );
        })}
      </ul>

      <QueueCard
        title="Needs a doctor"
        description="Paid appointments waiting for a doctor, earliest first."
        href="/staff/appointments?queue=needs_doctor&ordering=slot_time"
        resource={needsDoctor}
        empty="No appointments are waiting for a doctor."
      />
      <QueueCard
        title="Today"
        description="Today's appointments in India time."
        href="/staff/appointments?queue=today&ordering=slot_time"
        resource={today}
        empty="No appointments today."
      />
    </div>
  );
}

function QueueCard({
  title,
  description,
  href,
  resource,
  empty,
}: {
  title: string;
  description: string;
  href: string;
  resource: ReturnType<typeof useStaffResource<Paginated<AppointmentItem>>>;
  empty: string;
}) {
  const { data, error, loading } = resource;
  return (
    <Card
      title={title}
      description={description}
      actions={
        <Link href={href} className={btnClasses("ghost", "sm")}>
          View all{data ? ` (${data.count})` : ""} <ArrowRight className="h-4 w-4" aria-hidden />
        </Link>
      }
    >
      {Boolean(error) && <ErrorAlert error={error} />}
      {!data && loading && <Spinner />}
      {data && <AppointmentsTable items={data.results.slice(0, 10)} caption={title} emptyMessage={empty} />}
    </Card>
  );
}
