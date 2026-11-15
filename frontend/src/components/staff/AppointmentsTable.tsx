"use client";

import Link from "next/link";
import { AlertTriangle, ChevronLeft, ChevronRight, Lock } from "lucide-react";
import type { AppointmentItem } from "@/lib/staff/types";
import { formatDateTime } from "@/lib/staff/time";
import { Badge, PaymentBadge, StatusBadge, btnClasses } from "@/components/staff/ui";

export function AppointmentsTable({
  items,
  caption,
  emptyMessage = "No appointments found.",
}: {
  items: AppointmentItem[];
  caption: string;
  emptyMessage?: string;
}) {
  if (items.length === 0) {
    return <p className="rounded-lg border border-dashed border-slate-300 px-4 py-8 text-center text-sm text-slate-500">{emptyMessage}</p>;
  }

  return (
    <div className="-mx-4 overflow-x-auto sm:mx-0">
      <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
        <caption className="sr-only">{caption}</caption>
        <thead className="bg-slate-50 text-xs font-semibold uppercase tracking-wide text-slate-500">
          <tr>
            <th scope="col" className="px-3 py-2.5">Appointment</th>
            <th scope="col" className="px-3 py-2.5">Date &amp; time</th>
            <th scope="col" className="px-3 py-2.5">Patient</th>
            <th scope="col" className="px-3 py-2.5">Category</th>
            <th scope="col" className="px-3 py-2.5">Doctor</th>
            <th scope="col" className="px-3 py-2.5">Status</th>
            <th scope="col" className="px-3 py-2.5">Payment</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {items.map((item) => (
            <tr key={item.id} className="align-top hover:bg-slate-50">
              <td className="px-3 py-3">
                <Link
                  href={`/staff/appointments/${item.id}`}
                  className="font-semibold text-primary-darker underline-offset-2 hover:underline focus-visible:rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                >
                  {item.appointment_number}
                </Link>
                <div className="mt-1 flex flex-wrap gap-1">
                  {item.is_overdue && (
                    <Badge className="bg-rose-50 text-rose-700 ring-rose-300">
                      <AlertTriangle className="h-3 w-3" aria-hidden /> Overdue
                    </Badge>
                  )}
                  {!item.can_assign && item.lock_reason && (
                    <span title={item.lock_reason}>
                      <Badge className="bg-slate-100 text-slate-600 ring-slate-300">
                        <Lock className="h-3 w-3" aria-hidden /> Locked
                        <span className="sr-only">: {item.lock_reason}</span>
                      </Badge>
                    </span>
                  )}
                  {item.needs_completion_confirmation && (
                    <Badge className="bg-sky-50 text-sky-800 ring-sky-300">Confirm completion</Badge>
                  )}
                </div>
              </td>
              <td className="whitespace-nowrap px-3 py-3 text-ink">
                {item.date_display ? `${item.date_display}, ${item.schedule_time}` : formatDateTime(item.slot_time)}
              </td>
              <td className="px-3 py-3">
                <p className="font-medium text-ink">{item.patient_name || "—"}</p>
                <p className="text-xs text-slate-500">
                  {item.patient_relation_label || item.patient_relation}
                  {item.patient_phone ? ` · ${item.patient_phone}` : ""}
                </p>
              </td>
              <td className="px-3 py-3 text-ink">
                {item.category?.title || item.category?.name || "—"}
                {item.mode_label && <p className="text-xs text-slate-500">{item.mode_label}</p>}
              </td>
              <td className="px-3 py-3">
                {item.doctor ? (
                  <>
                    <p className="text-ink">{item.doctor.name}</p>
                    <p className="text-xs text-slate-500">{item.doctor.specialization}</p>
                  </>
                ) : (
                  <span className="text-xs font-semibold uppercase tracking-wide text-orange-700">Unassigned</span>
                )}
              </td>
              <td className="px-3 py-3">
                <StatusBadge status={item.status} label={item.status_label} />
                {(item.booker_account_deleted || item.doctor_account_deleted) && (
                  <p className="mt-1 text-xs font-semibold text-amber-800">Account deleted - review needed</p>
                )}
              </td>
              <td className="px-3 py-3">
                <PaymentBadge status={item.payment_status} />
                {item.amount_display && <p className="mt-1 text-xs text-slate-500">{item.amount_display}</p>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Pagination({
  page,
  count,
  pageSize = 20,
  hasNext,
  hasPrevious,
  onChange,
}: {
  page: number;
  count: number;
  pageSize?: number;
  hasNext: boolean;
  hasPrevious: boolean;
  onChange: (page: number) => void;
}) {
  const totalPages = Math.max(1, Math.ceil(count / pageSize));
  if (count === 0) return null;
  const from = (page - 1) * pageSize + 1;
  const to = Math.min(count, page * pageSize);
  return (
    <nav aria-label="Pagination" className="flex flex-wrap items-center justify-between gap-3 pt-4 text-sm text-slate-600">
      <p>
        Showing <span className="font-semibold text-ink">{from}</span>–<span className="font-semibold text-ink">{to}</span> of{" "}
        <span className="font-semibold text-ink">{count}</span> · Page {page} of {totalPages}
      </p>
      <div className="flex gap-2">
        <button type="button" className={btnClasses("secondary", "sm")} disabled={!hasPrevious} onClick={() => onChange(page - 1)}>
          <ChevronLeft className="h-4 w-4" aria-hidden /> Previous
        </button>
        <button type="button" className={btnClasses("secondary", "sm")} disabled={!hasNext} onClick={() => onChange(page + 1)}>
          Next <ChevronRight className="h-4 w-4" aria-hidden />
        </button>
      </div>
    </nav>
  );
}
