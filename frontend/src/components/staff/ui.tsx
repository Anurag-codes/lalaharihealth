"use client";

import { useEffect, useId, useRef, type ReactNode } from "react";
import { clsx } from "clsx";
import { AlertCircle, CheckCircle2, Loader2 } from "lucide-react";
import type { AppointmentStatus, PaymentStatus } from "@/lib/staff/types";
import { errorMessages } from "@/lib/staff/client";

export const STATUS_OPTIONS: { value: AppointmentStatus; label: string }[] = [
  { value: "pending", label: "Pending" },
  { value: "awaiting_payment", label: "Awaiting payment" },
  { value: "finding_doctor", label: "Finding doctor" },
  { value: "confirmed", label: "Confirmed" },
  { value: "completed", label: "Completed" },
  { value: "cancelled", label: "Cancelled" },
];

export const QUEUE_OPTIONS = [
  { value: "needs_doctor", label: "Needs a doctor" },
  { value: "overdue", label: "Overdue" },
  { value: "today", label: "Today" },
  { value: "awaiting_payment", label: "Awaiting payment" },
  { value: "completion_pending", label: "Completion pending" },
  { value: "upcoming", label: "Upcoming" },
] as const;

export const ORDERING_OPTIONS = [
  { value: "slot_time", label: "Appointment time (earliest first)" },
  { value: "-slot_time", label: "Appointment time (latest first)" },
  { value: "-created_at", label: "Booked (newest first)" },
  { value: "created_at", label: "Booked (oldest first)" },
] as const;

export const GENDER_OPTIONS = [
  { value: "male", label: "Male" },
  { value: "female", label: "Female" },
  { value: "other", label: "Other" },
  { value: "prefer_not_to_say", label: "Prefer not to say" },
] as const;

export const inputClasses =
  "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-ink shadow-sm transition placeholder:text-slate-400 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/30 disabled:cursor-not-allowed disabled:bg-slate-100";

export const labelClasses = "mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600";

type BtnVariant = "primary" | "secondary" | "danger" | "ghost";

export function btnClasses(variant: BtnVariant = "primary", size: "sm" | "md" = "md", className?: string) {
  return clsx(
    "inline-flex items-center justify-center gap-2 rounded-lg font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
    size === "sm" ? "px-3 py-1.5 text-xs" : "px-4 py-2 text-sm",
    variant === "primary" && "bg-primary text-white hover:bg-primary-dark",
    variant === "secondary" && "border border-slate-300 bg-white text-ink hover:bg-slate-50",
    variant === "danger" && "bg-rose-600 text-white hover:bg-rose-700",
    variant === "ghost" && "text-primary-darker hover:bg-primary-light",
    className,
  );
}

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-slate-100 text-slate-700 ring-slate-300",
  awaiting_payment: "bg-amber-50 text-amber-800 ring-amber-300",
  finding_doctor: "bg-orange-50 text-orange-800 ring-orange-300",
  confirmed: "bg-primary-light text-primary-darker ring-primary/40",
  completed: "bg-emerald-50 text-emerald-800 ring-emerald-300",
  cancelled: "bg-rose-50 text-rose-800 ring-rose-300",
};

export function Badge({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-semibold ring-1 ring-inset",
        className,
      )}
    >
      {children}
    </span>
  );
}

export function StatusBadge({ status, label }: { status: AppointmentStatus | string; label?: string }) {
  return (
    <Badge className={STATUS_STYLES[status] ?? STATUS_STYLES.pending}>
      {label || STATUS_OPTIONS.find((s) => s.value === status)?.label || status}
    </Badge>
  );
}

const PAYMENT_STYLES: Record<PaymentStatus, { label: string; className: string }> = {
  not_required: { label: "Free consultation", className: "bg-emerald-50 text-emerald-800 ring-emerald-300" },
  not_started: { label: "Not started", className: "bg-slate-100 text-slate-600 ring-slate-300" },
  pending: { label: "Pending", className: "bg-amber-50 text-amber-800 ring-amber-300" },
  success: { label: "Paid", className: "bg-emerald-50 text-emerald-800 ring-emerald-300" },
  failed: { label: "Failed", className: "bg-rose-50 text-rose-800 ring-rose-300" },
  refunded: { label: "Refunded", className: "bg-violet-50 text-violet-800 ring-violet-300" },
};

export function PaymentBadge({ status }: { status: PaymentStatus | string }) {
  const style = PAYMENT_STYLES[status as PaymentStatus] ?? { label: status, className: PAYMENT_STYLES.not_started.className };
  return <Badge className={style.className}>{style.label}</Badge>;
}

export function Card({
  title,
  description,
  actions,
  className,
  children,
  id,
}: {
  title?: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  className?: string;
  children: ReactNode;
  id?: string;
}) {
  return (
    <section id={id} className={clsx("rounded-xl border border-slate-200 bg-white shadow-sm", className)}>
      {(title || actions) && (
        <header className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 px-4 py-3 sm:px-5">
          <div>
            {title && <h2 className="font-heading text-base font-semibold text-ink">{title}</h2>}
            {description && <p className="mt-0.5 text-sm text-slate-500">{description}</p>}
          </div>
          {actions}
        </header>
      )}
      <div className="px-4 py-4 sm:px-5">{children}</div>
    </section>
  );
}

export function ErrorAlert({ error, messages, title }: { error?: unknown; messages?: string[]; title?: string }) {
  const list = messages ?? (error ? errorMessages(error) : []);
  return (
    <div role="alert" aria-live="assertive">
      {list.length > 0 && (
        <div className="flex gap-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2.5 text-sm text-rose-800">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
          <div>
            {title && <p className="font-semibold">{title}</p>}
            {list.length === 1 ? (
              <p>{list[0]}</p>
            ) : (
              <ul className="list-disc space-y-0.5 pl-4">
                {list.map((m, i) => (
                  <li key={i}>{m}</li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export function SuccessAlert({ message }: { message: string | null }) {
  return (
    <div role="status" aria-live="polite">
      {message && (
        <div className="flex gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2.5 text-sm text-emerald-800">
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
          <p>{message}</p>
        </div>
      )}
    </div>
  );
}

export function Spinner({ label = "Loading…", className }: { label?: string; className?: string }) {
  return (
    <span role="status" className={clsx("inline-flex items-center gap-2 text-sm text-slate-500", className)}>
      <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
      {label}
    </span>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed border-slate-300 px-4 py-8 text-center">
      <p className="font-medium text-ink">{title}</p>
      {children && <div className="mt-1 text-sm text-slate-500">{children}</div>}
    </div>
  );
}

export function ConfirmDialog({
  open,
  title,
  children,
  confirmLabel = "Confirm",
  busy = false,
  error,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  children: ReactNode;
  confirmLabel?: string;
  busy?: boolean;
  error?: unknown;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      onCancel={(e) => {
        e.preventDefault();
        if (!busy) onCancel();
      }}
      className="m-auto w-[min(32rem,calc(100vw-2rem))] rounded-xl border border-slate-200 bg-white p-0 text-ink shadow-2xl backdrop:bg-slate-900/50"
    >
      {open && (
        <div className="p-5">
          <h2 id={titleId} className="font-heading text-lg font-semibold">
            {title}
          </h2>
          <div className="mt-3 space-y-3 text-sm text-slate-700">{children}</div>
          {Boolean(error) && (
            <div className="mt-3">
              <ErrorAlert error={error} />
            </div>
          )}
          <div className="mt-5 flex flex-wrap justify-end gap-2">
            <button type="button" className={btnClasses("secondary")} onClick={onCancel} disabled={busy}>
              Cancel
            </button>
            <button type="button" className={btnClasses("primary")} onClick={onConfirm} disabled={busy} autoFocus>
              {busy && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
              {confirmLabel}
            </button>
          </div>
        </div>
      )}
    </dialog>
  );
}

export function DefinitionList({ items }: { items: { label: string; value: ReactNode }[] }) {
  return (
    <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-2">
      {items.map((item) => (
        <div key={item.label} className="min-w-0">
          <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{item.label}</dt>
          <dd className="mt-0.5 break-words text-sm text-ink">{item.value === "" || item.value === null || item.value === undefined ? "—" : item.value}</dd>
        </div>
      ))}
    </dl>
  );
}
