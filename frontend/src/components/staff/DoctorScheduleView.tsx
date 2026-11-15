"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, ChevronLeft, ChevronRight } from "lucide-react";
import { StaffApiError, useStaffResource, withQuery } from "@/lib/staff/client";
import type { DoctorSchedule } from "@/lib/staff/types";
import { addDays, formatDate, isValidDateString } from "@/lib/staff/time";
import { ScheduleGrid, ScheduleLegend, useIndiaNow } from "@/components/staff/TimeGrids";
import { Card, EmptyState, ErrorAlert, StatusBadge, Spinner, btnClasses, inputClasses, labelClasses } from "@/components/staff/ui";

export function DoctorScheduleView({ doctorId }: { doctorId: string }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const now = useIndiaNow();
  const rawDate = searchParams.get("date");
  const date = isValidDateString(rawDate) ? rawDate : now.date;

  const { data, error, loading, reload } = useStaffResource<DoctorSchedule>(
    withQuery(`staff/doctors/${doctorId}/schedule`, { date }),
  );

  function goTo(nextDate: string) {
    if (isValidDateString(nextDate)) router.replace(`${pathname}?date=${nextDate}`, { scroll: false });
  }

  const booked = data?.times.filter((t) => t.appointment) ?? [];
  const openSlots = data?.times.filter((t) => t.slot_open && !t.appointment && !t.is_past).length ?? 0;
  const notFound = error instanceof StaffApiError && error.status === 404;

  return (
    <div className="space-y-6">
      <Link href="/staff/doctors" className={btnClasses("ghost", "sm", "-ml-3")}>
        <ArrowLeft className="h-4 w-4" aria-hidden /> All doctors
      </Link>
      <div>
        <h1 className="font-heading text-2xl font-bold text-ink">{data?.doctor.name ?? "Doctor schedule"}</h1>
        {data?.doctor.specialization && <p className="text-sm text-slate-500">{data.doctor.specialization}</p>}
      </div>

      <Card>
        <div className="flex flex-wrap items-end gap-2">
          <button type="button" className={btnClasses("secondary", "sm")} onClick={() => goTo(addDays(date, -1))}>
            <ChevronLeft className="h-4 w-4" aria-hidden /> Previous day
          </button>
          <div>
            <label htmlFor="schedule-date" className={labelClasses}>
              Date
            </label>
            <input
              id="schedule-date"
              type="date"
              value={date}
              onChange={(e) => goTo(e.target.value)}
              className={inputClasses}
            />
          </div>
          <button type="button" className={btnClasses("secondary", "sm")} onClick={() => goTo(addDays(date, 1))}>
            Next day <ChevronRight className="h-4 w-4" aria-hidden />
          </button>
          <button
            type="button"
            className={btnClasses("ghost", "sm")}
            onClick={() => goTo(now.date)}
            disabled={date === now.date}
          >
            Today
          </button>
        </div>
      </Card>

      {notFound ? (
        <EmptyState title="Doctor not found">This doctor may be inactive or unverified.</EmptyState>
      ) : (
        Boolean(error) && (
          <div className="space-y-2">
            <ErrorAlert error={error} title="Couldn't load the schedule" />
            <button type="button" className={btnClasses("secondary", "sm")} onClick={reload}>
              Try again
            </button>
          </div>
        )
      )}

      {!data && loading && <Spinner label="Loading schedule…" />}

      {data && (
        <>
          <Card
            title={`Appointments on ${formatDate(data.date)}`}
            description={`${booked.length} booked · ${openSlots} open slot${openSlots === 1 ? "" : "s"} remaining`}
            actions={loading ? <Spinner label="Updating…" /> : undefined}
          >
            {booked.length === 0 ? (
              <p className="text-sm text-slate-500">No appointments on this day.</p>
            ) : (
              <ul className="divide-y divide-slate-100">
                {booked.map((t) => (
                  <li key={t.starts_at} className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm">
                    <span className="flex items-center gap-3">
                      <span className="w-20 font-semibold tabular-nums text-ink">{t.time_display}</span>
                      <Link href={`/staff/appointments/${t.appointment!.id}`} className="font-semibold text-primary-darker hover:underline">
                        {t.appointment!.appointment_number}
                      </Link>
                      <span className="text-slate-600">{t.appointment!.patient_name}</span>
                    </span>
                    <StatusBadge status={t.appointment!.status} />
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card title="Day schedule (IST)" actions={<ScheduleLegend />}>
            <div aria-busy={loading}>
              <ScheduleGrid schedule={data} />
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
