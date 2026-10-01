"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Building2, Stethoscope, X } from "lucide-react";
import { FlashingBadge } from "@/components/ui/FlashingBadge";

export function RegistrationOfferPopup() {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => setIsOpen(true), 2000);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!isOpen) return;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setIsOpen(false);
    };
    window.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-start justify-center overflow-y-auto bg-ink/65 p-3 backdrop-blur-sm sm:items-center sm:p-6"
      onClick={(event) => {
        if (event.target === event.currentTarget) setIsOpen(false);
      }}
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="registration-offer-title"
        className="my-auto w-full max-w-2xl overflow-hidden rounded-2xl bg-white shadow-2xl sm:rounded-3xl"
      >
        <div className="flex items-center justify-between border-b border-black/5 px-5 py-4 sm:px-8">
          <FlashingBadge>Free for first 100 registrations</FlashingBadge>
          <button
            type="button"
            onClick={() => setIsOpen(false)}
            aria-label="Close registration offer"
            className="flex h-11 w-11 items-center justify-center rounded-full text-ink/60 hover:bg-primary-light hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        <div className="px-5 py-6 sm:px-8 sm:py-8">
          <h1
            id="registration-offer-title"
            className="font-heading text-3xl font-extrabold leading-tight text-ink sm:text-4xl"
          >
            A golden opportunity to grow through online consultations
          </h1>

          <p className="mt-4 text-base leading-relaxed text-ink/70 sm:text-lg">
            For doctors, hospitals, clinics and labs: register with LalahariHealth and connect
            with people seeking affordable health consultations.
          </p>

          <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="flex items-start gap-3 rounded-xl bg-primary-soft p-4">
              <Stethoscope className="mt-0.5 h-5 w-5 shrink-0 text-primary-darker" />
              <p className="text-sm leading-relaxed text-ink/70">
                We&apos;re onboarding Allopathic and Naturopathy/home-remedy practitioners now.
                Ayurvedic, Unani and Homeopathic practitioners are welcome too.
              </p>
            </div>
            <div className="flex items-start gap-3 rounded-xl bg-primary-soft p-4">
              <Building2 className="mt-0.5 h-5 w-5 shrink-0 text-primary-darker" />
              <p className="text-sm leading-relaxed text-ink/70">
                Hospitals, clinics and labs can register to introduce their services to people
                looking for care.
              </p>
            </div>
          </div>

          <p className="mt-5 rounded-xl border border-primary/20 bg-primary-light px-4 py-3 text-sm font-semibold leading-relaxed text-primary-darker sm:text-base">
            Registration is free for the first 100 registrations. Apply now to be considered for
            priority placement when the app launches.
          </p>

          <div className="mt-7 flex flex-col gap-3 sm:flex-row sm:items-center">
            <a
              href="#apply"
              onClick={() => setIsOpen(false)}
              className="inline-flex min-h-14 w-full items-center justify-center rounded-full bg-primary px-8 py-4 text-base font-semibold text-white shadow-lg shadow-primary/25 transition-colors hover:bg-primary-dark sm:w-auto sm:text-lg"
            >
              Register now
            </a>
            <Link
              href="#apply"
              onClick={() => setIsOpen(false)}
              className="rounded-full px-5 py-3 text-center text-sm font-semibold text-primary-darker underline underline-offset-4 hover:bg-primary-light sm:ml-1"
            >
              Choose doctor or hospital registration
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
