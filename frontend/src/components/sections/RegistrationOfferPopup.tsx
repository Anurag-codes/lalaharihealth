"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Building2, Stethoscope, X } from "lucide-react";
import { FlashingBadge } from "@/components/ui/FlashingBadge";
import { useCloseAfterBottomScroll } from "@/hooks/useCloseAfterBottomScroll";

export function RegistrationOfferPopup() {
  const [isOpen, setIsOpen] = useState(false);
  const closePopup = () => setIsOpen(false);
  const scrollDismissHandlers = useCloseAfterBottomScroll(closePopup);

  useEffect(() => {
    const timer = window.setTimeout(() => setIsOpen(true), 2000);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!isOpen) return;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") closePopup();
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
      {...scrollDismissHandlers}
      onClick={(event) => {
        if (event.target === event.currentTarget) closePopup();
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
            onClick={closePopup}
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

          <div className="mt-5 rounded-2xl border border-black/5 bg-white p-4 sm:p-5">
            <h2 className="font-heading text-3xl font-extrabold leading-tight text-primary-darker sm:text-4xl">
              Potential to earn in Thousands and Lakhs*
            </h2>
            <p className="mt-1 text-sm text-ink/60">
              General doctors charge a fixed ₹200. Specialists choose ₹200–₹2,000. Doctors receive
              75% of the fee after the 25% platform fee.
            </p>
            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="rounded-xl bg-primary-soft p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-ink/50">
                  General doctor · 5 completed consults/day
                </p>
                <p className="mt-1 font-heading text-2xl font-extrabold text-primary-darker">₹15,000/month</p>
                <p className="text-xs text-ink/50">₹150 payout × 5/day × 20 days</p>
              </div>
              <div className="rounded-xl bg-primary-soft p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-ink/50">
                  Specialist at ₹2,000 · 5 completed consults/day
                </p>
                <p className="mt-1 font-heading text-2xl font-extrabold text-primary-darker">₹1.5 lakh/month</p>
                <p className="text-xs text-ink/50">₹1,500 payout × 5/day × 20 days</p>
              </div>
            </div>
            <p className="mt-3 text-xs leading-relaxed text-ink/45">
              *Illustrative payout estimates, not guaranteed income. They assume every consultation
              is completed and paid; actual booking volume may differ, and a higher fee may affect
              demand. Taxes, refunds or other adjustments may affect payouts. Transfers are within
              48 hours after completion and payment confirmation.
            </p>
          </div>

          <div className="mt-7 flex flex-col gap-3 sm:flex-row sm:items-center">
            <a
              href="#apply"
              onClick={closePopup}
              className="inline-flex min-h-14 w-full items-center justify-center rounded-full bg-primary px-8 py-4 text-base font-semibold text-white shadow-lg shadow-primary/25 transition-colors hover:bg-primary-dark sm:w-auto sm:text-lg"
            >
              Register now
            </a>
            <Link
              href="#apply"
              onClick={closePopup}
              className="rounded-full px-5 py-3 text-center text-sm font-semibold text-primary-darker underline underline-offset-4 hover:bg-primary-light sm:ml-1"
            >
              Choose doctor or hospital registration
            </Link>
          </div>
          <p className="mt-5 text-center text-xs text-ink/45">
            At the end, scroll down twice to close this offer.
          </p>
        </div>
      </section>
    </div>
  );
}
