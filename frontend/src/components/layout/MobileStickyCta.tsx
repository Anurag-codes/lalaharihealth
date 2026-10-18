"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { ClipboardList, Phone, PhoneCall, X } from "lucide-react";
import { BookConsultationButton } from "@/components/ui/BookConsultationButton";
import { CallbackForm } from "@/components/booking/CallbackForm";

const BAR_CLASSES =
  "fixed inset-x-0 bottom-0 z-40 border-t border-black/5 bg-white/95 p-3 backdrop-blur-md shadow-[0_-4px_20px_rgba(0,0,0,0.06)] lg:hidden";
const ICON_ACTION_CLASSES =
  "flex flex-1 flex-col items-center justify-center gap-1 rounded-2xl py-1.5 text-xs font-semibold";

function DoctorStickyActions() {
  const [showCallback, setShowCallback] = useState(false);

  useEffect(() => {
    if (!showCallback) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setShowCallback(false);
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [showCallback]);

  return (
    <>
      {showCallback && (
        <div
          className="fixed inset-0 z-[60] flex items-end bg-ink/50 backdrop-blur-sm lg:hidden"
          onClick={(event) => {
            if (event.target === event.currentTarget) setShowCallback(false);
          }}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="doctor-callback-title"
            className="animate-fade-up w-full rounded-t-3xl bg-white p-5 pb-8 shadow-2xl"
          >
            <div className="mb-4 flex items-center justify-between">
              <h2 id="doctor-callback-title" className="font-heading text-lg font-bold text-ink">
                Request a callback
              </h2>
              <button
                type="button"
                onClick={() => setShowCallback(false)}
                aria-label="Close"
                className="flex h-10 w-10 items-center justify-center rounded-full text-ink/60 hover:bg-primary-light"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <CallbackForm autoFocus purpose="doctor-registration" />
          </div>
        </div>
      )}

      <nav aria-label="Register options" className={`${BAR_CLASSES} flex items-stretch gap-2`}>
        <a href="tel:+911800000000" className={`${ICON_ACTION_CLASSES} text-primary-darker`}>
          <span className="flex h-10 w-10 items-center justify-center rounded-full border-2 border-primary">
            <Phone className="h-5 w-5" />
          </span>
          Call
        </a>
        <button
          type="button"
          onClick={() => setShowCallback(true)}
          className={`${ICON_ACTION_CLASSES} text-primary-darker`}
        >
          <span className="flex h-10 w-10 items-center justify-center rounded-full border-2 border-primary">
            <PhoneCall className="h-5 w-5" />
          </span>
          Request
        </button>
        <a href="#apply" className={`${ICON_ACTION_CLASSES} text-primary-darker`}>
          <span className="flex h-10 w-10 items-center justify-center rounded-full bg-primary text-white shadow-md shadow-primary/30">
            <ClipboardList className="h-5 w-5" />
          </span>
          Register
        </a>
      </nav>
    </>
  );
}

export function MobileStickyCta() {
  const pathname = usePathname();

  if (pathname === "/for-doctors") return <DoctorStickyActions />;

  return (
    <div className={`${BAR_CLASSES} flex items-center gap-3`}>
      <a
        href="tel:+911800000000"
        aria-label="Call us"
        className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full border-2 border-primary text-primary-darker"
      >
        <Phone className="h-5 w-5" />
      </a>
      <BookConsultationButton className="flex-1">
        Free Registration
      </BookConsultationButton>
    </div>
  );
}
