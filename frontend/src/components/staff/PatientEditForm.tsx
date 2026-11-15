"use client";

import { useState, type FormEvent } from "react";
import { Info, Loader2, Pencil } from "lucide-react";
import { staffFetch } from "@/lib/staff/client";
import type { AppointmentDetail } from "@/lib/staff/types";
import { ErrorAlert, GENDER_OPTIONS, btnClasses, inputClasses, labelClasses } from "@/components/staff/ui";

type PatientPatch = { patient_name?: string; patient_age?: number; patient_gender?: string };

export function PatientEditForm({
  appointment,
  onSaved,
}: {
  appointment: AppointmentDetail;
  onSaved: (updated: AppointmentDetail) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(appointment.patient_name ?? "");
  const [age, setAge] = useState(appointment.patient_age === null ? "" : String(appointment.patient_age));
  const [gender, setGender] = useState(appointment.patient_gender ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [validation, setValidation] = useState<string[]>([]);

  function reset() {
    setName(appointment.patient_name ?? "");
    setAge(appointment.patient_age === null ? "" : String(appointment.patient_age));
    setGender(appointment.patient_gender ?? "");
    setError(null);
    setValidation([]);
  }

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const problems: string[] = [];
    const patch: PatientPatch = {};
    const trimmed = name.trim();
    if (!trimmed) problems.push("Patient name is required.");
    else if (trimmed !== appointment.patient_name) patch.patient_name = trimmed;

    if (age.trim() === "") {
      problems.push("Patient age is required.");
    } else {
      const n = Number(age);
      if (!Number.isInteger(n) || n < 0 || n > 120) problems.push("Age must be a whole number between 0 and 120.");
      else if (n !== appointment.patient_age) patch.patient_age = n;
    }
    if (gender && gender !== appointment.patient_gender) patch.patient_gender = gender;

    if (problems.length) {
      setValidation(problems);
      return;
    }
    setValidation([]);
    if (Object.keys(patch).length === 0) {
      setEditing(false);
      return;
    }

    setSaving(true);
    setError(null);
    try {
      const updated = await staffFetch<AppointmentDetail>(`staff/appointments/${appointment.id}/patient`, {
        method: "PATCH",
        body: patch,
      });
      setEditing(false);
      onSaved(updated);
    } catch (err) {
      setError(err);
    } finally {
      setSaving(false);
    }
  }

  const phoneNote = (
    <p className="flex items-start gap-1.5 text-xs text-slate-500">
      <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
      The phone number can&apos;t be changed here — it controls which family member&apos;s app account can access this
      appointment.
    </p>
  );

  if (!editing) {
    return (
      <div className="space-y-3">
        {appointment.can_edit_patient ? (
          <button
            type="button"
            className={btnClasses("secondary", "sm")}
            onClick={() => {
              reset();
              setEditing(true);
            }}
          >
            <Pencil className="h-3.5 w-3.5" aria-hidden /> Edit patient details
          </button>
        ) : (
          <p className="text-xs text-slate-500">Patient details can no longer be edited for this appointment.</p>
        )}
        {phoneNote}
      </div>
    );
  }

  return (
    <form onSubmit={onSubmit} className="space-y-3 rounded-lg border border-slate-200 bg-slate-50 p-3" noValidate>
      <ErrorAlert messages={validation.length ? validation : undefined} error={validation.length ? undefined : error} />
      <div>
        <label htmlFor="patient-name" className={labelClasses}>
          Patient name
        </label>
        <input
          id="patient-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={150}
          required
          className={inputClasses}
          autoComplete="off"
        />
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label htmlFor="patient-age" className={labelClasses}>
            Age
          </label>
          <input
            id="patient-age"
            type="number"
            inputMode="numeric"
            min={0}
            max={120}
            step={1}
            value={age}
            onChange={(e) => setAge(e.target.value)}
            className={inputClasses}
          />
        </div>
        <div>
          <label htmlFor="patient-gender" className={labelClasses}>
            Gender
          </label>
          <select id="patient-gender" value={gender} onChange={(e) => setGender(e.target.value)} className={inputClasses}>
            {!appointment.patient_gender && <option value="">Not specified</option>}
            {GENDER_OPTIONS.map((g) => (
              <option key={g.value} value={g.value}>
                {g.label}
              </option>
            ))}
          </select>
        </div>
      </div>
      {phoneNote}
      <div className="flex justify-end gap-2">
        <button type="button" className={btnClasses("secondary", "sm")} onClick={() => setEditing(false)} disabled={saving}>
          Cancel
        </button>
        <button type="submit" className={btnClasses("primary", "sm")} disabled={saving}>
          {saving && <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />}
          Save
        </button>
      </div>
    </form>
  );
}
