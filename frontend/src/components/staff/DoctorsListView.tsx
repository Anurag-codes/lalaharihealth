"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { CalendarDays, Search } from "lucide-react";
import { useStaffResource, withQuery } from "@/lib/staff/client";
import type { StaffDoctor } from "@/lib/staff/types";
import { getIndiaNow } from "@/lib/staff/time";
import { SpecialitySelect, useSpecialities } from "@/components/staff/AppointmentsListView";
import { Card, ErrorAlert, Spinner, btnClasses, inputClasses, labelClasses } from "@/components/staff/ui";

export function DoctorsListView() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const q = searchParams.get("q") ?? "";
  const speciality = searchParams.get("speciality") ?? "";
  const [searchText, setSearchText] = useState(q);
  const [lastQ, setLastQ] = useState(q);
  if (q !== lastQ) {
    setLastQ(q);
    setSearchText(q);
  }

  const { data, error, loading, reload } = useStaffResource<StaffDoctor[]>(withQuery("staff/doctors", { q, speciality }));
  const specialities = useSpecialities();
  const [today] = useState(() => getIndiaNow().date);

  function update(changes: Record<string, string>) {
    const next = new URLSearchParams(searchParams.toString());
    for (const [key, value] of Object.entries(changes)) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    const qs = next.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  }

  function onSearch(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    update({ q: searchText.trim() });
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-heading text-2xl font-bold text-ink">Doctors</h1>
        <p className="text-sm text-slate-500">Verified, active doctors. Open a doctor to see their day schedule.</p>
      </div>

      <Card>
        <div className="grid gap-3 md:grid-cols-[1fr_16rem]">
          <form onSubmit={onSearch} role="search">
            <label htmlFor="doctor-search" className={labelClasses}>
              Search
            </label>
            <div className="flex gap-2">
              <input
                id="doctor-search"
                type="search"
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                placeholder="Name, phone or specialization…"
                className={inputClasses}
              />
              <button type="submit" className={btnClasses("primary")}>
                <Search className="h-4 w-4" aria-hidden /> <span className="sr-only sm:not-sr-only">Search</span>
              </button>
            </div>
          </form>
          <div>
            <label htmlFor="doctor-speciality" className={labelClasses}>
              Speciality
            </label>
            <SpecialitySelect
              id="doctor-speciality"
              value={speciality}
              onChange={(v) => update({ speciality: v })}
              specialities={specialities.list}
            />
          </div>
        </div>
      </Card>

      <Card
        title="Doctors"
        description={data ? `${data.length} doctor${data.length === 1 ? "" : "s"}` : undefined}
        actions={loading && data ? <Spinner label="Updating…" /> : undefined}
      >
        {Boolean(error) && (
          <div className="mb-3 space-y-2">
            <ErrorAlert error={error} title="Couldn't load doctors" />
            <button type="button" className={btnClasses("secondary", "sm")} onClick={reload}>
              Try again
            </button>
          </div>
        )}
        {!data && loading && <Spinner />}
        {data && data.length === 0 && (
          <p className="rounded-lg border border-dashed border-slate-300 px-4 py-8 text-center text-sm text-slate-500">
            No doctors match these filters.
          </p>
        )}
        {data && data.length > 0 && (
          <div className="-mx-4 overflow-x-auto sm:mx-0" aria-busy={loading}>
            <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
              <caption className="sr-only">Doctors</caption>
              <thead className="bg-slate-50 text-xs font-semibold uppercase tracking-wide text-slate-500">
                <tr>
                  <th scope="col" className="px-3 py-2.5">Doctor</th>
                  <th scope="col" className="px-3 py-2.5">Speciality</th>
                  <th scope="col" className="px-3 py-2.5">Experience</th>
                  <th scope="col" className="px-3 py-2.5">City</th>
                  <th scope="col" className="px-3 py-2.5">Phone</th>
                  <th scope="col" className="px-3 py-2.5">Upcoming</th>
                  <th scope="col" className="px-3 py-2.5"><span className="sr-only">Actions</span></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {data.map((d) => (
                  <tr key={d.id} className="hover:bg-slate-50">
                    <td className="px-3 py-3">
                      <Link
                        href={`/staff/doctors/${d.id}?date=${today}`}
                        className="font-semibold text-primary-darker hover:underline focus-visible:rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                      >
                        {d.name}
                      </Link>
                      {d.specialization && <p className="text-xs text-slate-500">{d.specialization}</p>}
                    </td>
                    <td className="px-3 py-3">{d.speciality?.name ?? "General"}</td>
                    <td className="px-3 py-3">{d.experience_years ? `${d.experience_years} yrs` : "—"}</td>
                    <td className="px-3 py-3">{d.city || "—"}</td>
                    <td className="whitespace-nowrap px-3 py-3">
                      {d.phone ? (
                        <a href={`tel:${d.phone}`} className="hover:underline">
                          {d.phone}
                        </a>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="px-3 py-3 tabular-nums">{d.upcoming_appointments}</td>
                    <td className="px-3 py-3 text-right">
                      <Link href={`/staff/doctors/${d.id}?date=${today}`} className={btnClasses("secondary", "sm")}>
                        <CalendarDays className="h-3.5 w-3.5" aria-hidden /> Schedule
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
