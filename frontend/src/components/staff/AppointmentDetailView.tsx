"use client";

import { useState, type ReactNode } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowLeft,
  CheckCheck,
  Download,
  FileText,
  Lock,
  Phone,
  RefreshCw,
  Video,
} from "lucide-react";
import { StaffApiError, proxyDownloadUrl, staffFetch, useStaffResource } from "@/lib/staff/client";
import type { AppointmentDetail } from "@/lib/staff/types";
import { formatDateTime, formatDuration } from "@/lib/staff/time";
import { AssignPanel } from "@/components/staff/AssignPanel";
import { PatientEditForm } from "@/components/staff/PatientEditForm";
import {
  Badge,
  Card,
  ConfirmDialog,
  DefinitionList,
  EmptyState,
  ErrorAlert,
  PaymentBadge,
  Spinner,
  StatusBadge,
  SuccessAlert,
  btnClasses,
} from "@/components/staff/ui";

function yesNo(value: boolean | null | undefined) {
  if (value === null || value === undefined) return "—";
  return value ? "Yes" : "No";
}

function Text({ children }: { children: ReactNode }) {
  return <span className="whitespace-pre-line">{children}</span>;
}

export function AppointmentDetailView({ id }: { id: string }) {
  const { data, error, loading, reload, setData } = useStaffResource<AppointmentDetail>(`staff/appointments/${id}`);
  const [message, setMessage] = useState<string | null>(null);
  const [completionOpen, setCompletionOpen] = useState(false);
  const [completing, setCompleting] = useState(false);
  const [completionError, setCompletionError] = useState<unknown>(null);

  async function confirmCompletion() {
    setCompleting(true);
    setCompletionError(null);
    try {
      await staffFetch(`appointments/${id}/confirm-completion`, { method: "POST", body: {} });
      setCompletionOpen(false);
      setMessage("Completion confirmed.");
      reload();
    } catch (err) {
      setCompletionError(err);
    } finally {
      setCompleting(false);
    }
  }

  const backLink = (
    <Link href="/staff/appointments" className={btnClasses("ghost", "sm", "-ml-3")}>
      <ArrowLeft className="h-4 w-4" aria-hidden /> All appointments
    </Link>
  );

  if (!data) {
    const notFound = error instanceof StaffApiError && error.status === 404;
    return (
      <div className="space-y-4">
        {backLink}
        {loading && <Spinner label="Loading appointment…" />}
        {notFound ? (
          <EmptyState title="Appointment not found">It may have been removed, or the link is wrong.</EmptyState>
        ) : (
          Boolean(error) && (
            <div className="space-y-2">
              <ErrorAlert error={error} title="Couldn't load this appointment" />
              <button type="button" className={btnClasses("secondary", "sm")} onClick={reload}>
                Try again
              </button>
            </div>
          )
        )}
      </div>
    );
  }

  const a = data;
  const timeline: { label: string; value: string | null }[] = [
    { label: "Booked", value: a.timeline.created_at },
    { label: "Information confirmed", value: a.timeline.information_confirmed_at },
    { label: "Paid", value: a.timeline.paid_at },
    { label: "Doctor assigned", value: a.timeline.doctor_assigned_at },
    { label: "Completed", value: a.timeline.completed_at },
    { label: "Completion confirmed", value: a.timeline.completion_confirmed_at },
    { label: "Cancelled", value: a.timeline.cancelled_at },
  ];

  return (
    <div className="space-y-6">
      {backLink}
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="font-heading text-2xl font-bold text-ink">{a.appointment_number}</h1>
            <StatusBadge status={a.status} label={a.status_label} />
            {a.is_overdue && (
              <Badge className="bg-rose-50 text-rose-700 ring-rose-300">
                <AlertTriangle className="h-3 w-3" aria-hidden /> Overdue
              </Badge>
            )}
          </div>
          <p className="mt-1 text-sm text-slate-600">
            {a.date_display ? `${a.date_display}, ${a.schedule_time}` : formatDateTime(a.slot_time)} · {a.category?.title || a.category?.name} · {a.mode_label}
          </p>
          <p className="text-sm text-slate-600">
            Doctor:{" "}
            {a.doctor ? (
              <span className="font-medium text-ink">
                {a.doctor.name}
                {a.doctor.specialization ? ` (${a.doctor.specialization})` : ""}
              </span>
            ) : (
              <span className="font-semibold text-orange-700">Unassigned</span>
            )}
          </p>
        </div>
        <button type="button" onClick={reload} className={btnClasses("secondary", "sm")} disabled={loading}>
          <RefreshCw className={loading ? "h-4 w-4 animate-spin" : "h-4 w-4"} aria-hidden /> Refresh
        </button>
      </header>

      <SuccessAlert message={message} />
      {Boolean(error) && <ErrorAlert error={error} title="Couldn't refresh this appointment" />}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="min-w-0 space-y-6 lg:col-span-2">
          {(a.booker_account_deleted || a.doctor_account_deleted) && (
            <Card title="Account deleted - staff action required">
              <p className="text-sm text-amber-800">
                {a.booker_account_deleted ? "The booking account has been deleted. " : ""}
                {a.doctor_account_deleted ? "The assigned doctor has deleted their account. " : ""}
                Records and payment remain unchanged. Contact support to resolve outstanding care,
                reassignment or refunds; do not transfer records to a new account automatically.
              </p>
            </Card>
          )}
          {a.needs_completion_confirmation && (
            <Card title="Completion needs confirmation" description="The doctor marked this consultation as completed.">
              <button
                type="button"
                className={btnClasses("primary")}
                onClick={() => {
                  setCompletionError(null);
                  setCompletionOpen(true);
                }}
              >
                <CheckCheck className="h-4 w-4" aria-hidden /> Confirm completion
              </button>
              {!completionOpen && Boolean(completionError) && (
                <div className="mt-3">
                  <ErrorAlert error={completionError} />
                </div>
              )}
            </Card>
          )}

          {a.can_assign ? (
            <AssignPanel
              key={`${a.id}-${a.slot_time}-${a.doctor?.id ?? "none"}-${a.status}`}
              appointment={a}
              onAssigned={(msg) => {
                setMessage(msg);
                reload();
              }}
            />
          ) : (
            <Card title="Doctor & schedule">
              <p className="flex items-start gap-2 text-sm text-slate-600">
                <Lock className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" aria-hidden />
                {a.lock_reason || "This appointment can't be reassigned or rescheduled right now."}
              </p>
            </Card>
          )}

          <Card title="Case details">
            <DefinitionList
              items={[
                { label: "Chief complaint", value: <Text>{a.chief_complaint}</Text> },
                { label: "Symptoms", value: <Text>{a.symptoms}</Text> },
                { label: "Duration", value: a.duration_display },
                { label: "Ongoing medication", value: yesNo(a.ongoing_medication) },
                { label: "Condition details", value: <Text>{a.condition_details || "—"}</Text> },
                { label: "Treatment details", value: <Text>{a.treatment_details || "—"}</Text> },
                { label: "Consultation", value: a.consultation_status ? `#${a.consultation_id} · ${a.consultation_status}` : "—" },
              ]}
            />
          </Card>

          <Card title="Documents">
            {a.documents.length === 0 ? (
              <p className="text-sm text-slate-500">No documents uploaded.</p>
            ) : (
              <ul className="divide-y divide-slate-100">
                {a.documents.map((doc) => {
                  const href = proxyDownloadUrl(doc.download_path);
                  return (
                    <li key={doc.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                      <span className="flex min-w-0 items-center gap-2 text-sm">
                        <FileText className="h-4 w-4 shrink-0 text-slate-400" aria-hidden />
                        <span className="min-w-0">
                          <span className="block truncate font-medium text-ink">{doc.original_name}</span>
                          <span className="block text-xs text-slate-500">Uploaded {formatDateTime(doc.uploaded_at)}</span>
                        </span>
                      </span>
                      {href ? (
                        <a href={href} className={btnClasses("secondary", "sm")} download>
                          <Download className="h-3.5 w-3.5" aria-hidden /> Download
                          <span className="sr-only"> {doc.original_name}</span>
                        </a>
                      ) : (
                        <span className="text-xs text-slate-400">Unavailable</span>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </Card>

          <Card title="Calls">
            <p className="mb-3 flex items-center gap-2 text-sm text-slate-600">
              <Video className="h-4 w-4 text-slate-400" aria-hidden />
              Video room {a.video_room_provisioned ? "provisioned" : "not provisioned yet"}
            </p>
            {a.calls.length === 0 ? (
              <p className="text-sm text-slate-500">No calls yet.</p>
            ) : (
              <div className="-mx-4 overflow-x-auto sm:mx-0">
                <table className="min-w-full text-left text-sm">
                  <caption className="sr-only">Calls</caption>
                  <thead className="bg-slate-50 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    <tr>
                      <th scope="col" className="px-3 py-2">Mode</th>
                      <th scope="col" className="px-3 py-2">Status</th>
                      <th scope="col" className="px-3 py-2">Started</th>
                      <th scope="col" className="px-3 py-2">Ended</th>
                      <th scope="col" className="px-3 py-2">Duration</th>
                      <th scope="col" className="px-3 py-2">End reason</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {a.calls.map((c) => (
                      <tr key={c.id}>
                        <td className="px-3 py-2 capitalize">
                          {c.mode}
                          {c.provider ? <span className="block text-xs text-slate-500">{c.provider}</span> : null}
                        </td>
                        <td className="px-3 py-2">{c.status_label || c.status}</td>
                        <td className="whitespace-nowrap px-3 py-2">{formatDateTime(c.started_at)}</td>
                        <td className="whitespace-nowrap px-3 py-2">{formatDateTime(c.ended_at)}</td>
                        <td className="px-3 py-2">{formatDuration(c.duration_seconds)}</td>
                        <td className="px-3 py-2">{c.end_reason || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>

        <div className="min-w-0 space-y-6">
          <Card title="Patient">
            <div className="space-y-4">
              <DefinitionList
                items={[
                  { label: "Name", value: a.patient_name },
                  { label: "Age", value: a.patient_age ?? "—" },
                  { label: "Gender", value: a.patient_gender_label || a.patient_gender },
                  { label: "Relation", value: a.patient_relation_label || a.patient_relation },
                  {
                    label: "Phone",
                    value: a.patient_phone ? (
                      <a href={`tel:${a.patient_phone}`} className="inline-flex items-center gap-1 text-primary-darker hover:underline">
                        <Phone className="h-3.5 w-3.5" aria-hidden /> {a.patient_phone}
                      </a>
                    ) : (
                      "—"
                    ),
                  },
                ]}
              />
              <PatientEditForm
                key={`${a.patient_name}-${a.patient_age}-${a.patient_gender}`}
                appointment={a}
                onSaved={(updated) => {
                  setData(updated);
                  setMessage("Patient details updated.");
                }}
              />
            </div>
          </Card>

          <Card title="Booked by">
            <DefinitionList
              items={[
                { label: "Name", value: a.booker?.name },
                {
                  label: "Phone",
                  value: a.booker?.phone ? (
                    <a href={`tel:${a.booker.phone}`} className="text-primary-darker hover:underline">
                      {a.booker.phone}
                    </a>
                  ) : (
                    "—"
                  ),
                },
                { label: "Email", value: a.booker?.email || "—" },
              ]}
            />
          </Card>

          <Card title="Payment">
            <div className="mb-3 flex items-center gap-2">
              <PaymentBadge status={a.payment_status} />
              <span className="text-sm font-semibold text-ink">{a.amount_display}</span>
            </div>
            {a.payment ? (
              <DefinitionList
                items={[
                  { label: "Method", value: a.payment.method },
                  { label: "Status", value: a.payment.status },
                  { label: "Amount", value: `${a.payment.amount} ${a.payment.currency}` },
                  { label: "Created", value: formatDateTime(a.payment.created_at) },
                  { label: "Order ID", value: <span className="break-all font-mono text-xs">{a.payment.gateway_order_id || "—"}</span> },
                  { label: "Transaction ID", value: <span className="break-all font-mono text-xs">{a.payment.transaction_id || "—"}</span> },
                ]}
              />
            ) : (
              <p className="text-sm text-slate-500">
                {a.payment_status === "not_required"
                  ? `Free consultation approved with code ${a.coupon_code}. No payment required.`
                  : "No payment record."}
              </p>
            )}
          </Card>

          <Card title="Timeline">
            <ol className="space-y-2">
              {timeline.map((t) => (
                <li key={t.label} className="flex justify-between gap-3 text-sm">
                  <span className={t.value ? "text-ink" : "text-slate-400"}>{t.label}</span>
                  <span className={t.value ? "text-right text-slate-600" : "text-slate-300"}>
                    {t.value ? formatDateTime(t.value) : "—"}
                  </span>
                </li>
              ))}
            </ol>
            {a.timeline.completion_confirmed_by && (
              <p className="mt-2 text-xs text-slate-500">Completion confirmed by {a.timeline.completion_confirmed_by}</p>
            )}
          </Card>
        </div>
      </div>

      <ConfirmDialog
        open={completionOpen}
        title="Confirm completion?"
        confirmLabel="Confirm completion"
        busy={completing}
        error={completionError}
        onConfirm={confirmCompletion}
        onCancel={() => setCompletionOpen(false)}
      >
        <p>
          Confirm that appointment <span className="font-semibold">{a.appointment_number}</span> with{" "}
          {a.doctor?.name ?? "the doctor"} was completed.
        </p>
      </ConfirmDialog>
    </div>
  );
}
