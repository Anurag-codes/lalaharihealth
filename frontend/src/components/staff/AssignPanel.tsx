"use client";

import { useMemo, useState } from "react";
import { clsx } from "clsx";
import { AlertTriangle, CalendarClock, CalendarSearch, Loader2, Search, UserCheck } from "lucide-react";
import { StaffApiError, staffFetch, useStaffResource, withQuery } from "@/lib/staff/client";
import type { AppointmentDetail, DoctorSchedule, EligibleDoctor, EligibleDoctorsResponse } from "@/lib/staff/types";
import {
  BOOKING_WINDOW_DAYS,
  addDays,
  buildStartsAt,
  formatDate,
  formatDateTime,
  formatSlotLabel,
  isSlotPast,
  isValidDateString,
  toIndiaDateMinutes,
} from "@/lib/staff/time";
import { Badge, Card, ConfirmDialog, ErrorAlert, Spinner, btnClasses, inputClasses, labelClasses } from "@/components/staff/ui";
import { ScheduleGrid, ScheduleLegend, SlotGrid, useIndiaNow } from "@/components/staff/TimeGrids";

function availabilityBadges(doctor: EligibleDoctor) {
  const badges: { label: string; className: string }[] = [];
  if (doctor.is_current) badges.push({ label: "Current doctor", className: "bg-primary-light text-primary-darker ring-primary/40" });
  if (!doctor.is_available) {
    badges.push({
      label: doctor.conflict ? `Busy with ${doctor.conflict.appointment_number}` : "Busy",
      className: "bg-rose-50 text-rose-700 ring-rose-300",
    });
  } else if (doctor.has_open_slot) {
    badges.push({ label: "Has open slot", className: "bg-emerald-50 text-emerald-800 ring-emerald-300" });
  } else {
    badges.push({ label: "Available", className: "bg-sky-50 text-sky-800 ring-sky-300" });
  }
  return badges;
}

function rank(d: EligibleDoctor) {
  if (!d.is_available) return 3;
  if (d.is_current) return 0;
  return d.has_open_slot ? 1 : 2;
}

export function AssignPanel({
  appointment,
  onAssigned,
}: {
  appointment: AppointmentDetail;
  onAssigned: (message: string) => void;
}) {
  const now = useIndiaNow();
  const original = toIndiaDateMinutes(appointment.slot_time);
  const originalStartsAt = original ? buildStartsAt(original.date, original.minutes) : null;
  const currentDoctorId = appointment.doctor?.id ?? null;
  const isFinding = appointment.status === "finding_doctor";
  const minDate = now.date;
  const maxDate = addDays(now.date, BOOKING_WINDOW_DAYS);

  const [date, setDate] = useState(original?.date ?? now.date);
  const [minutes, setMinutes] = useState<number | null>(original?.minutes ?? null);
  const [doctorId, setDoctorId] = useState<number | null>(currentDoctorId);
  const [doctorFilter, setDoctorFilter] = useState("");
  const [showSchedule, setShowSchedule] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<unknown>(null);

  const startsAt = minutes !== null ? buildStartsAt(date, minutes) : null;
  const timeChanged = startsAt !== null && startsAt !== originalStartsAt;
  const doctorChanged = doctorId !== null && doctorId !== currentDoctorId;
  const selectedPast = minutes !== null && isSlotPast(date, minutes, now);
  const dateOutOfRange = date < minDate || date > maxDate;

  const doctorsPath = startsAt
    ? withQuery(`staff/appointments/${appointment.id}/doctors`, { starts_at: startsAt })
    : null;
  const doctors = useStaffResource<EligibleDoctorsResponse>(doctorsPath);
  const doctorList = useMemo(() => {
    const list = [...(doctors.data?.results ?? [])].sort((a, b) => rank(a) - rank(b));
    const q = doctorFilter.trim().toLowerCase();
    if (!q) return list;
    return list.filter((d) =>
      [d.name, d.specialization, d.speciality_name ?? ""].some((v) => v.toLowerCase().includes(q)),
    );
  }, [doctors.data, doctorFilter]);
  const selectedDoctor = doctors.data?.results.find((d) => d.id === doctorId) ?? null;

  const schedulePath =
    showSchedule && doctorId !== null && isValidDateString(date)
      ? withQuery(`staff/doctors/${doctorId}/schedule`, { date })
      : null;
  const schedule = useStaffResource<DoctorSchedule>(schedulePath);

  const body: { doctor_id?: number; starts_at?: string } = {};
  if (isFinding) {
    if (doctorId !== null) body.doctor_id = doctorId;
  } else if (doctorChanged && doctorId !== null) {
    body.doctor_id = doctorId;
  }
  if (timeChanged && startsAt) body.starts_at = startsAt;

  const problems: string[] = [];
  if (isFinding && doctorId === null) problems.push("Choose a doctor.");
  if (!isFinding && !doctorChanged && !timeChanged) problems.push("Change the doctor or the time to continue.");
  if (minutes === null) problems.push("Choose a time.");
  if (timeChanged && selectedPast) problems.push("The selected time has already passed.");
  if (timeChanged && dateOutOfRange) problems.push(`Pick a date between today and ${formatDate(maxDate)}.`);
  if (!timeChanged && original && isSlotPast(original.date, original.minutes, now)) {
    problems.push("The current appointment time has passed. Pick a new future time.");
  }
  if (selectedDoctor && !selectedDoctor.is_available) problems.push(`${selectedDoctor.name} is busy at this time.`);
  const canSubmit = problems.length === 0 && !doctors.loading && !submitting;

  const newDoctorName = selectedDoctor?.name ?? appointment.doctor?.name ?? (doctorId ? `Doctor #${doctorId}` : "—");

  async function submit() {
    setSubmitting(true);
    setSubmitError(null);
    try {
      await staffFetch(`appointments/${appointment.id}/assign-doctor`, { method: "POST", body });
      setConfirmOpen(false);
      const parts: string[] = [];
      if (body.doctor_id !== undefined) parts.push(`doctor ${isFinding && !appointment.doctor ? "assigned" : "set"} to ${newDoctorName}`);
      if (body.starts_at) parts.push(`time moved to ${formatDateTime(body.starts_at)}`);
      onAssigned(`Appointment ${appointment.appointment_number} updated: ${parts.join(" and ")}. The patient and doctor have been notified.`);
    } catch (err) {
      setSubmitError(err);
      if (err instanceof StaffApiError && err.status === 400) doctors.reload();
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card
      id="assign"
      title={isFinding ? "Assign a doctor" : "Reassign or reschedule"}
      description="Times are in India time (IST). Pick a date and 15-minute slot, then an available doctor."
    >
      <div className="space-y-6">
        {appointment.coupon_code && (
          <p className="rounded-lg bg-primary-light p-3 text-sm text-primary-darker">
            Free consultation (code {appointment.coupon_code}). Only the offer doctor can be assigned;
            choose another time if that doctor is busy. No payment is required.
          </p>
        )}
        <div className="grid gap-4 sm:grid-cols-[minmax(0,14rem)_1fr]">
          <div>
            <label htmlFor="assign-date" className={labelClasses}>
              Date
            </label>
            <input
              id="assign-date"
              type="date"
              value={date}
              min={minDate}
              max={maxDate}
              onChange={(e) => {
                if (isValidDateString(e.target.value)) setDate(e.target.value);
              }}
              className={inputClasses}
              aria-describedby="assign-date-help"
            />
            <p id="assign-date-help" className="mt-1 text-xs text-slate-500">
              Today to {formatDate(maxDate)}.
            </p>
          </div>
          <div className="rounded-lg bg-slate-50 px-3 py-2 text-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Current</p>
            <p className="text-ink">
              {formatDateTime(appointment.slot_time)} · {appointment.doctor?.name ?? "No doctor"}
            </p>
            <p className="mt-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Selected</p>
            <p className={clsx("text-ink", (timeChanged || doctorChanged) && "font-semibold text-primary-darker")}>
              {startsAt ? formatDateTime(startsAt) : "No time selected"} · {doctorId !== null ? newDoctorName : "No doctor"}
            </p>
          </div>
        </div>

        <div>
          <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-ink">
            <CalendarClock className="h-4 w-4 text-primary" aria-hidden /> Time on {formatDate(date)}
          </h3>
          <SlotGrid
            date={date}
            selected={minutes}
            onSelect={setMinutes}
            now={now}
            currentMinutes={original && original.date === date ? original.minutes : null}
          />
        </div>

        <fieldset>
          <legend className="mb-2 flex items-center gap-2 text-sm font-semibold text-ink">
            <UserCheck className="h-4 w-4 text-primary" aria-hidden /> Doctor
            {startsAt && <span className="font-normal text-slate-500">— availability at {formatDateTime(startsAt)}</span>}
          </legend>
          <div className="relative mb-3 max-w-sm">
            <label htmlFor="doctor-filter" className="sr-only">
              Filter doctors by name or speciality
            </label>
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden />
            <input
              id="doctor-filter"
              type="search"
              value={doctorFilter}
              onChange={(e) => setDoctorFilter(e.target.value)}
              placeholder="Filter by name or speciality"
              className={`${inputClasses} pl-9`}
            />
          </div>
          {!startsAt && <p className="text-sm text-slate-500">Choose a time to see doctor availability.</p>}
          {Boolean(doctors.error) && <ErrorAlert error={doctors.error} title="Couldn't load doctors" />}
          {doctors.loading && <Spinner label="Checking availability…" className="mb-2" />}
          {doctors.data && doctorList.length === 0 && (
            <p className="text-sm text-slate-500">
              {doctorFilter ? "No doctors match this filter." : "No eligible doctors for this appointment."}
            </p>
          )}
          {doctors.data && doctorList.length > 0 && (
            <ul className={clsx("grid gap-2 md:grid-cols-2", doctors.loading && "opacity-60")} aria-busy={doctors.loading}>
              {doctorList.map((d) => {
                const disabled = !d.is_available;
                const checked = doctorId === d.id;
                return (
                  <li key={d.id}>
                    <label
                      className={clsx(
                        "flex h-full cursor-pointer gap-3 rounded-lg border p-3 transition focus-within:ring-2 focus-within:ring-primary",
                        checked ? "border-primary bg-primary-soft" : "border-slate-200 bg-white hover:border-primary/50",
                        disabled && "cursor-not-allowed opacity-60 hover:border-slate-200",
                      )}
                    >
                      <input
                        type="radio"
                        name="assign-doctor"
                        className="mt-1 h-4 w-4 accent-primary"
                        checked={checked}
                        disabled={disabled}
                        onChange={() => setDoctorId(d.id)}
                      />
                      <span className="min-w-0 flex-1">
                        <span className="block font-semibold text-ink">{d.name}</span>
                        <span className="block text-xs text-slate-500">
                          {[d.specialization, d.speciality_name, d.experience_years ? `${d.experience_years} yrs exp.` : null]
                            .filter(Boolean)
                            .join(" · ") || "General"}
                        </span>
                        <span className="mt-1.5 flex flex-wrap items-center gap-1">
                          {availabilityBadges(d).map((b) => (
                            <Badge key={b.label} className={b.className}>
                              {b.label}
                            </Badge>
                          ))}
                          <span className="text-xs text-slate-500">
                            {d.appointments_that_day} appointment{d.appointments_that_day === 1 ? "" : "s"} that day
                          </span>
                        </span>
                      </span>
                    </label>
                  </li>
                );
              })}
            </ul>
          )}
        </fieldset>

        {doctorId !== null && (
          <div>
            <button
              type="button"
              className={btnClasses("secondary", "sm")}
              aria-expanded={showSchedule}
              aria-controls="assign-schedule"
              onClick={() => setShowSchedule((v) => !v)}
            >
              <CalendarSearch className="h-4 w-4" aria-hidden />
              {showSchedule ? "Hide day schedule" : `View ${newDoctorName}'s day schedule`}
            </button>
            {showSchedule && (
              <div id="assign-schedule" className="mt-3 space-y-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-sm font-semibold text-ink">
                    {schedule.data?.doctor.name ?? newDoctorName} · {formatDate(date)}
                  </p>
                  <ScheduleLegend />
                </div>
                <p className="text-xs text-slate-500">Click a free time to choose it.</p>
                {Boolean(schedule.error) && <ErrorAlert error={schedule.error} />}
                {schedule.loading && <Spinner />}
                {schedule.data && (
                  <ScheduleGrid
                    schedule={schedule.data}
                    currentAppointmentId={appointment.id}
                    selectedStartsAt={startsAt}
                    onPick={setMinutes}
                  />
                )}
              </div>
            )}
          </div>
        )}

        <div className="flex flex-col gap-3 border-t border-slate-100 pt-4 sm:flex-row sm:items-center sm:justify-between">
          <div aria-live="polite" className="text-sm">
            {problems.length > 0 ? (
              <p className="flex items-start gap-1.5 text-amber-800">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
                {problems[0]}
              </p>
            ) : (
              <>
                <p className="text-slate-600">
                  Will send:{" "}
                  {[
                    body.doctor_id !== undefined ? `doctor → ${newDoctorName}` : null,
                    body.starts_at ? `time → ${formatDateTime(body.starts_at)}` : null,
                  ]
                    .filter(Boolean)
                    .join(", ")}
                </p>
              </>
            )}
          </div>
          <button
            type="button"
            className={btnClasses("primary")}
            disabled={!canSubmit}
            onClick={() => {
              setSubmitError(null);
              setConfirmOpen(true);
            }}
          >
            {submitting && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
            {isFinding ? "Assign doctor" : "Save changes"}
          </button>
        </div>
        {!confirmOpen && Boolean(submitError) && <ErrorAlert error={submitError} title="Couldn't update the appointment" />}
      </div>

      <ConfirmDialog
        open={confirmOpen}
        title={isFinding ? "Assign this doctor?" : "Save these changes?"}
        confirmLabel={isFinding ? "Assign doctor" : "Save changes"}
        busy={submitting}
        error={submitError}
        onConfirm={submit}
        onCancel={() => setConfirmOpen(false)}
      >
        <p>
          Appointment <span className="font-semibold">{appointment.appointment_number}</span> for{" "}
          <span className="font-semibold">{appointment.patient_name}</span>
        </p>
        <dl className="space-y-2 rounded-lg bg-slate-50 p-3">
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Doctor</dt>
            <dd>
              {body.doctor_id !== undefined ? (
                <>
                  {appointment.doctor?.name ?? "Unassigned"} → <span className="font-semibold">{newDoctorName}</span>
                </>
              ) : (
                <>{appointment.doctor?.name ?? "Unassigned"} (unchanged)</>
              )}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Date &amp; time (IST)</dt>
            <dd>
              {body.starts_at ? (
                <>
                  {formatDateTime(appointment.slot_time)} →{" "}
                  <span className="font-semibold">
                    {formatDate(date)}, {minutes !== null ? formatSlotLabel(minutes) : ""}
                  </span>
                </>
              ) : (
                <>{formatDateTime(appointment.slot_time)} (unchanged)</>
              )}
            </dd>
          </div>
        </dl>
        <p className="text-slate-600">The patient and the doctor will be notified about this change.</p>
      </ConfirmDialog>
    </Card>
  );
}
