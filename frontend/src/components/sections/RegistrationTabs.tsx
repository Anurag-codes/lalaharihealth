"use client";

import { useState } from "react";
import { Building2, Stethoscope } from "lucide-react";
import { DoctorOnboardingForm } from "@/components/sections/DoctorOnboardingForm";
import { HospitalOnboardingForm } from "@/components/sections/HospitalOnboardingForm";

type Tab = "doctor" | "hospital";

export function RegistrationTabs() {
  const [tab, setTab] = useState<Tab>("doctor");

  return (
    <div>
      <div className="mx-auto flex max-w-md rounded-full border-2 border-black/10 bg-white p-1.5">
        <button
          type="button"
          onClick={() => setTab("doctor")}
          aria-pressed={tab === "doctor"}
          className={
            tab === "doctor"
              ? "flex flex-1 items-center justify-center gap-2 rounded-full bg-primary px-4 py-2.5 text-sm font-semibold text-white shadow-md shadow-primary/25"
              : "flex flex-1 items-center justify-center gap-2 rounded-full px-4 py-2.5 text-sm font-medium text-ink/60"
          }
        >
          <Stethoscope className="h-4 w-4" />
          I&apos;m a Doctor
        </button>
        <button
          type="button"
          onClick={() => setTab("hospital")}
          aria-pressed={tab === "hospital"}
          className={
            tab === "hospital"
              ? "flex flex-1 items-center justify-center gap-2 rounded-full bg-primary px-4 py-2.5 text-sm font-semibold text-white shadow-md shadow-primary/25"
              : "flex flex-1 items-center justify-center gap-2 rounded-full px-4 py-2.5 text-sm font-medium text-ink/60"
          }
        >
          <Building2 className="h-4 w-4" />
          I&apos;m a Hospital/Clinic
        </button>
      </div>

      <div className="mt-8">
        {tab === "doctor" ? (
          <DoctorOnboardingForm />
        ) : (
          <HospitalOnboardingForm />
        )}
      </div>
    </div>
  );
}
