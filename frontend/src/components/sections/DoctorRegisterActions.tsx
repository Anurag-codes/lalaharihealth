"use client";

import { useState } from "react";
import { ClipboardList, Phone, PhoneCall } from "lucide-react";
import { CallbackForm } from "@/components/booking/CallbackForm";

const OPTION_CLASSES =
  "flex min-h-14 w-full items-center justify-center gap-2 rounded-full px-5 py-3.5 text-center text-base font-bold leading-snug transition-colors";

export function DoctorRegisterActions({
  onFormLinkClick,
  className = "",
}: {
  onFormLinkClick?: () => void;
  className?: string;
}) {
  const [showCallback, setShowCallback] = useState(false);

  return (
    <div className={`space-y-3 ${className}`}>
      <a
        href="tel:+911800000000"
        className={`${OPTION_CLASSES} bg-primary text-white shadow-lg shadow-primary/25 hover:bg-primary-dark`}
      >
        <Phone className="h-5 w-5 shrink-0" />
        Call us to get yourself register for free
      </a>

      {showCallback ? (
        <CallbackForm autoFocus purpose="doctor-registration" />
      ) : (
        <button
          type="button"
          onClick={() => setShowCallback(true)}
          className={`${OPTION_CLASSES} border-2 border-primary bg-white text-primary-darker hover:bg-primary-light`}
        >
          <PhoneCall className="h-5 w-5 shrink-0" />
          Request a callback
        </button>
      )}

      <a
        href="#apply"
        onClick={onFormLinkClick}
        className={`${OPTION_CLASSES} border-2 border-primary-darker/15 bg-primary-light text-primary-darker hover:bg-primary-soft`}
      >
        <ClipboardList className="h-5 w-5 shrink-0" />
        Fill form and get yourself register for free
      </a>
    </div>
  );
}
