"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { clsx } from "clsx";
import type { DoctorSchedule } from "@/lib/staff/types";
import { DAY_SLOTS, formatSlotLabel, getIndiaNow, isSlotPast, toIndiaDateMinutes } from "@/lib/staff/time";

/** India "now" that ticks every 30 seconds so past slots get disabled as time moves on. */
export function useIndiaNow() {
  const [now, setNow] = useState(getIndiaNow);
  useEffect(() => {
    const timer = window.setInterval(() => setNow(getIndiaNow()), 30_000);
    return () => window.clearInterval(timer);
  }, []);
  return now;
}

const PERIODS = [
  { label: "Night (12 AM – 6 AM)", start: 0 },
  { label: "Morning (6 AM – 12 PM)", start: 6 * 60 },
  { label: "Afternoon (12 PM – 6 PM)", start: 12 * 60 },
  { label: "Evening (6 PM – 12 AM)", start: 18 * 60 },
];

/** 96-slot (15-minute) time picker for a given India date. */
export function SlotGrid({
  date,
  selected,
  onSelect,
  now,
  currentMinutes,
}: {
  date: string;
  selected: number | null;
  onSelect: (minutes: number) => void;
  now: { date: string; minutes: number };
  /** Minutes of the appointment's current slot when it falls on `date`. */
  currentMinutes?: number | null;
}) {
  return (
    <div className="space-y-3">
      {PERIODS.map((period) => {
        const slots = DAY_SLOTS.filter((m) => m >= period.start && m < period.start + 6 * 60);
        const allPast = slots.every((m) => isSlotPast(date, m, now));
        return (
          <fieldset key={period.start}>
            <legend className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
              {period.label}
              {allPast && <span className="ml-2 font-normal normal-case text-slate-400">(passed)</span>}
            </legend>
            <div className="grid grid-cols-3 gap-1.5 sm:grid-cols-6 xl:grid-cols-8">
              {slots.map((m) => {
                const past = isSlotPast(date, m, now);
                const isSelected = selected === m;
                const isCurrent = currentMinutes === m;
                return (
                  <button
                    key={m}
                    type="button"
                    disabled={past}
                    aria-pressed={isSelected}
                    onClick={() => onSelect(m)}
                    className={clsx(
                      "rounded-md border px-1 py-1.5 text-xs font-medium tabular-nums transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1",
                      isSelected
                        ? "border-primary bg-primary text-white"
                        : past
                          ? "cursor-not-allowed border-slate-100 bg-slate-50 text-slate-300 line-through"
                          : isCurrent
                            ? "border-primary/60 bg-primary-light text-primary-darker"
                            : "border-slate-200 bg-white text-ink hover:border-primary hover:bg-primary-soft",
                    )}
                    title={isCurrent ? "Current appointment time" : undefined}
                  >
                    {formatSlotLabel(m)}
                    {isCurrent && !isSelected && <span className="sr-only"> (current time)</span>}
                  </button>
                );
              })}
            </div>
          </fieldset>
        );
      })}
    </div>
  );
}

export function ScheduleLegend() {
  const items = [
    { label: "Free", className: "border-slate-200 bg-white" },
    { label: "Open slot", className: "border-emerald-300 bg-emerald-50" },
    { label: "Booked", className: "border-amber-300 bg-amber-50" },
    { label: "This appointment", className: "border-primary bg-primary-light" },
    { label: "Past", className: "border-slate-100 bg-slate-100" },
  ];
  return (
    <ul className="flex flex-wrap gap-3 text-xs text-slate-600" aria-label="Legend">
      {items.map((i) => (
        <li key={i.label} className="flex items-center gap-1.5">
          <span className={clsx("inline-block h-3 w-3 rounded-sm border", i.className)} aria-hidden />
          {i.label}
        </li>
      ))}
    </ul>
  );
}

/**
 * A doctor's day: 96 entries marking past / open slot / booked times. In pick mode, free
 * times are buttons; otherwise booked times link to their appointment.
 */
export function ScheduleGrid({
  schedule,
  currentAppointmentId,
  selectedStartsAt,
  onPick,
}: {
  schedule: DoctorSchedule;
  currentAppointmentId?: number;
  selectedStartsAt?: string | null;
  onPick?: (minutes: number) => void;
}) {
  const selectedTime = selectedStartsAt ? new Date(selectedStartsAt).getTime() : null;
  return (
    <ul className="grid grid-cols-2 gap-1.5 sm:grid-cols-4 xl:grid-cols-6">
      {schedule.times.map((t) => {
        const isThis = Boolean(t.appointment && t.appointment.id === currentAppointmentId);
        const booked = Boolean(t.appointment) && !isThis;
        const pickable = Boolean(onPick) && !t.is_past && !booked;
        const isSelected = selectedTime !== null && new Date(t.starts_at).getTime() === selectedTime;
        const minutes = toIndiaDateMinutes(t.starts_at)?.minutes ?? 0;
        const label = t.time_display || formatSlotLabel(minutes);
        const cellClass = clsx(
          "block h-full w-full rounded-md border px-2 py-1.5 text-left text-xs transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary",
          isSelected
            ? "border-primary bg-primary text-white"
            : isThis
              ? "border-primary bg-primary-light text-primary-darker"
              : booked
                ? "border-amber-300 bg-amber-50 text-amber-900"
                : t.is_past
                  ? "border-slate-100 bg-slate-100 text-slate-400"
                  : t.slot_open
                    ? "border-emerald-300 bg-emerald-50 text-emerald-900"
                    : "border-slate-200 bg-white text-ink",
          pickable && !isSelected && "hover:border-primary hover:bg-primary-soft",
        );
        const status = isThis
          ? "This appointment"
          : booked
            ? "Booked"
            : t.is_past
              ? "Past"
              : t.slot_open
                ? "Open slot"
                : "Free";
        const content = (
          <>
            <span className="block font-semibold tabular-nums">{label}</span>
            {t.appointment ? (
              <span className="block truncate">
                {t.appointment.appointment_number} · {t.appointment.patient_name}
              </span>
            ) : (
              <span className="block opacity-80">{status}</span>
            )}
          </>
        );
        return (
          <li key={t.starts_at}>
            {pickable ? (
              <button
                type="button"
                className={cellClass}
                aria-pressed={isSelected}
                onClick={() => onPick?.(minutes)}
                aria-label={`${label}, ${status}. Choose this time`}
              >
                {content}
              </button>
            ) : t.appointment && !onPick ? (
              <Link href={`/staff/appointments/${t.appointment.id}`} className={clsx(cellClass, "hover:underline")}>
                {content}
              </Link>
            ) : (
              <div className={cellClass}>
                {content}
                {t.appointment && <span className="sr-only"> ({status})</span>}
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
