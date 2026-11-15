"use client";

import { useState, type FormEvent } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { RotateCcw, Search } from "lucide-react";
import { normalizeList, useStaffResource, withQuery } from "@/lib/staff/client";
import type { AppointmentItem, Paginated, Speciality, StaffDoctor } from "@/lib/staff/types";
import { AppointmentsTable, Pagination } from "@/components/staff/AppointmentsTable";
import {
  Card,
  ErrorAlert,
  ORDERING_OPTIONS,
  QUEUE_OPTIONS,
  STATUS_OPTIONS,
  Spinner,
  btnClasses,
  inputClasses,
  labelClasses,
} from "@/components/staff/ui";

const FILTER_KEYS = ["q", "queue", "status", "date_from", "date_to", "speciality", "doctor_id", "ordering", "page"] as const;
type FilterKey = (typeof FILTER_KEYS)[number];

export function useSpecialities() {
  const res = useStaffResource<Speciality[] | Paginated<Speciality>>("doctors/specialities");
  return { ...res, list: normalizeList<Speciality>(res.data) };
}

export function SpecialitySelect({
  id,
  value,
  onChange,
  specialities,
}: {
  id: string;
  value: string;
  onChange: (value: string) => void;
  specialities: Speciality[];
}) {
  return (
    <select id={id} value={value} onChange={(e) => onChange(e.target.value)} className={inputClasses}>
      <option value="">All specialities</option>
      <option value="general">General (no speciality)</option>
      {specialities.map((s) => (
        <option key={s.id} value={String(s.id)}>
          {s.name}
        </option>
      ))}
    </select>
  );
}

export function AppointmentsListView() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const filters = Object.fromEntries(FILTER_KEYS.map((k) => [k, searchParams.get(k) ?? ""])) as Record<FilterKey, string>;
  const page = Math.max(1, Number.parseInt(filters.page, 10) || 1);
  const [searchText, setSearchText] = useState(filters.q);
  const [lastQ, setLastQ] = useState(filters.q);
  if (filters.q !== lastQ) {
    // Keep the input in sync when the URL changes (back/forward, card links).
    setLastQ(filters.q);
    setSearchText(filters.q);
  }

  const apiPath = withQuery("staff/appointments", { ...filters, page: page > 1 ? page : undefined });
  const { data, error, loading, reload } = useStaffResource<Paginated<AppointmentItem>>(apiPath);
  const specialities = useSpecialities();
  const doctors = useStaffResource<StaffDoctor[]>("staff/doctors");

  function update(changes: Partial<Record<FilterKey, string>>, resetPage = true) {
    const next = new URLSearchParams(searchParams.toString());
    for (const [key, value] of Object.entries(changes)) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    if (resetPage && !("page" in changes)) next.delete("page");
    const qs = next.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  }

  function onSearch(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    update({ q: searchText.trim() });
  }

  const hasFilters = FILTER_KEYS.some((k) => k !== "page" && filters[k]);
  const activeQueue = QUEUE_OPTIONS.find((q) => q.value === filters.queue);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-heading text-2xl font-bold text-ink">Appointments</h1>
        <p className="text-sm text-slate-500">
          {activeQueue ? `Queue: ${activeQueue.label}` : "Search and filter all appointments."}
        </p>
      </div>

      <Card title="Filters">
        <form onSubmit={onSearch} className="flex flex-col gap-2 sm:flex-row" role="search">
          <label htmlFor="apt-search" className="sr-only">
            Search appointments
          </label>
          <input
            id="apt-search"
            type="search"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            placeholder="Search APT number, patient name or phone…"
            className={inputClasses}
          />
          <button type="submit" className={btnClasses("primary")}>
            <Search className="h-4 w-4" aria-hidden /> Search
          </button>
        </form>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <label htmlFor="f-queue" className={labelClasses}>Queue</label>
            <select id="f-queue" value={filters.queue} onChange={(e) => update({ queue: e.target.value })} className={inputClasses}>
              <option value="">All</option>
              {QUEUE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="f-status" className={labelClasses}>Status</label>
            <select id="f-status" value={filters.status} onChange={(e) => update({ status: e.target.value })} className={inputClasses}>
              <option value="">All statuses</option>
              {STATUS_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="f-from" className={labelClasses}>From date</label>
            <input
              id="f-from"
              type="date"
              value={filters.date_from}
              max={filters.date_to || undefined}
              onChange={(e) => update({ date_from: e.target.value })}
              className={inputClasses}
            />
          </div>
          <div>
            <label htmlFor="f-to" className={labelClasses}>To date</label>
            <input
              id="f-to"
              type="date"
              value={filters.date_to}
              min={filters.date_from || undefined}
              onChange={(e) => update({ date_to: e.target.value })}
              className={inputClasses}
            />
          </div>
          <div>
            <label htmlFor="f-speciality" className={labelClasses}>Speciality</label>
            <SpecialitySelect
              id="f-speciality"
              value={filters.speciality}
              onChange={(v) => update({ speciality: v })}
              specialities={specialities.list}
            />
          </div>
          <div>
            <label htmlFor="f-doctor" className={labelClasses}>Doctor</label>
            <select id="f-doctor" value={filters.doctor_id} onChange={(e) => update({ doctor_id: e.target.value })} className={inputClasses}>
              <option value="">All doctors</option>
              {(doctors.data ?? []).map((d) => (
                <option key={d.id} value={String(d.id)}>
                  {d.name}
                  {d.specialization ? ` — ${d.specialization}` : ""}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="f-ordering" className={labelClasses}>Sort by</label>
            <select id="f-ordering" value={filters.ordering} onChange={(e) => update({ ordering: e.target.value })} className={inputClasses}>
              <option value="">Default</option>
              {ORDERING_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>
          <div className="flex items-end">
            <button
              type="button"
              className={btnClasses("secondary", "md", "w-full")}
              disabled={!hasFilters}
              onClick={() => {
                setSearchText("");
                router.replace(pathname, { scroll: false });
              }}
            >
              <RotateCcw className="h-4 w-4" aria-hidden /> Clear filters
            </button>
          </div>
        </div>
      </Card>

      <Card
        title="Results"
        description={data ? `${data.count} appointment${data.count === 1 ? "" : "s"}` : undefined}
        actions={loading && data ? <Spinner label="Updating…" /> : undefined}
      >
        {Boolean(error) && (
          <div className="mb-3 space-y-2">
            <ErrorAlert error={error} title="Couldn't load appointments" />
            <button type="button" className={btnClasses("secondary", "sm")} onClick={reload}>Try again</button>
          </div>
        )}
        {!data && loading && <Spinner />}
        {data && (
          <div aria-busy={loading}>
            <AppointmentsTable
              items={data.results}
              caption="Appointments"
              emptyMessage={hasFilters ? "No appointments match these filters." : "No appointments yet."}
            />
            <Pagination
              page={page}
              count={data.count}
              hasNext={Boolean(data.next)}
              hasPrevious={Boolean(data.previous)}
              onChange={(p) => update({ page: p > 1 ? String(p) : "" }, false)}
            />
          </div>
        )}
      </Card>
    </div>
  );
}
