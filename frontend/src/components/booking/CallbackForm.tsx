"use client";

import { useState, type FormEvent } from "react";
import { AlertCircle, CheckCircle2, Loader2 } from "lucide-react";
import { API_BASE_URL } from "@/lib/api";
import { usePricing } from "@/components/pricing/PricingContext";

type Status = "idle" | "submitting" | "success" | "error";

export function CallbackForm({
  autoFocus = false,
  purpose = "consultation",
}: {
  autoFocus?: boolean;
  purpose?: "consultation" | "doctor-registration";
}) {
  const [status, setStatus] = useState<Status>("idle");
  const fee = usePricing().general_fee_display;
  const forDoctor = purpose === "doctor-registration";

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setStatus("submitting");
    const formData = new FormData(event.currentTarget);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/core/contact-messages/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: formData.get("name"),
          phone_number: formData.get("phone_number"),
          message: forDoctor
            ? "Doctor/Hospital registration callback: wants to register for free on LalahariHealth."
            : `Callback requested for a human-assisted consultation (${fee}). Executive to explain the fee and confirm the appointment.`,
        }),
      });
      if (!response.ok) throw new Error("Request failed");
      setStatus("success");
    } catch {
      setStatus("error");
    }
  };

  if (status === "success") {
    return (
      <div role="status" className="flex flex-col items-center gap-2 rounded-2xl bg-primary-light px-4 py-6 text-center">
        <CheckCircle2 className="h-9 w-9 text-primary-darker" />
        <p className="text-sm font-semibold text-ink">
          {forDoctor
            ? "Callback requested. Our team will call you and get you registered for free."
            : `Callback requested. Our executive will explain the ${fee} consultation and confirm your appointment.`}
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      <input
        name="name"
        type="text"
        required
        autoFocus={autoFocus}
        placeholder="Your name"
        aria-label="Your name"
        className="w-full rounded-xl border border-black/10 bg-white px-4 py-3.5 text-base text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
      />
      <input
        name="phone_number"
        type="tel"
        required
        placeholder="Your phone number"
        aria-label="Your phone number"
        className="w-full rounded-xl border border-black/10 bg-white px-4 py-3.5 text-base text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
      />
      {status === "error" && (
        <div role="alert" className="flex items-center gap-2 rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700 sm:col-span-2">
          <AlertCircle className="h-4 w-4 shrink-0" />
          Something went wrong. Please call our executive instead.
        </div>
      )}
      <button
        type="submit"
        disabled={status === "submitting"}
        className="flex min-h-14 w-full items-center justify-center gap-2 rounded-full border-2 border-primary bg-white px-5 py-3.5 text-base font-bold text-primary-darker hover:bg-primary-light disabled:cursor-not-allowed disabled:opacity-70 sm:col-span-2"
      >
        {status === "submitting" ? (
          <>
            <Loader2 className="h-5 w-5 animate-spin" /> Sending...
          </>
        ) : forDoctor ? (
          "Request a Callback"
        ) : (
          `Request a Callback — ${fee} consultation`
        )}
      </button>
    </form>
  );
}
