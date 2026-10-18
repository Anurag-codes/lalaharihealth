"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { AlertCircle, CheckCircle2, Loader2 } from "lucide-react";
import { getButtonClasses } from "@/components/ui/Button";
import { API_BASE_URL } from "@/lib/api";

type Status = "idle" | "submitting" | "success" | "error";

const INPUT_CLASS = "mt-1.5 w-full rounded-xl border border-black/15 bg-white px-4 py-3 text-base text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20";

export function GrievanceForm() {
  const [status, setStatus] = useState<Status>("idle");
  const [reference, setReference] = useState<number | null>(null);
  const [errorMessage, setErrorMessage] = useState("");

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (status === "submitting") return;

    const form = event.currentTarget;
    const data = new FormData(form);
    const name = String(data.get("name") ?? "").trim();
    const phone = String(data.get("phone_number") ?? "").trim();
    const subject = String(data.get("subject") ?? "").trim();
    const details = String(data.get("details") ?? "").trim();

    if (!name || !phone || !subject || !details) {
      setErrorMessage("Please enter your name, phone number, subject and a description of what went wrong.");
      setStatus("error");
      return;
    }

    setErrorMessage("");
    setStatus("submitting");

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/core/contact-messages/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          phone_number: phone,
          email: String(data.get("email") ?? "").trim(),
          message: `[Grievance]\nSubject: ${subject}\n\n${details}\n\nThe submitter agreed to be contacted about this complaint and acknowledged the Privacy Policy.`,
        }),
      });

      if (!response.ok) {
        setErrorMessage("Your complaint could not be submitted. Please check your details and try again, or email care@lalaharihealth.com.");
        setStatus("error");
        return;
      }

      const result: unknown = await response.json();
      if (
        typeof result !== "object" || result === null || !("id" in result) ||
        typeof result.id !== "number" || !Number.isSafeInteger(result.id) || result.id <= 0
      ) {
        setErrorMessage("We could not confirm your complaint reference. Please contact care@lalaharihealth.com before submitting again.");
        setStatus("error");
        return;
      }

      setReference(result.id);
      setStatus("success");
      form.reset();
    } catch {
      setErrorMessage("We could not confirm your submission. Please check your connection or contact care@lalaharihealth.com before submitting again.");
      setStatus("error");
    }
  };

  if (status === "success") {
    return (
      <div role="status" className="rounded-2xl border border-primary/20 bg-primary-light p-6 sm:p-8">
        <CheckCircle2 className="h-10 w-10 text-primary-darker" />
        <h2 className="mt-4 font-heading text-xl font-bold text-ink">Your complaint has been received</h2>
        <p className="mt-3 text-ink/75">
          Reference: <strong>LH-{reference}</strong>. Please save this reference for follow-up.
          Our team will review your complaint and contact you using the details you provided.
        </p>
        <p className="mt-3 text-sm text-ink/65">
          To follow up, email care@lalaharihealth.com or call our founder on 9818677599.
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} aria-labelledby="complaint-form-title" className="rounded-2xl border border-black/10 bg-white p-5 sm:p-8">
      <h2 id="complaint-form-title" className="font-heading text-xl font-bold text-ink">Tell us what went wrong</h2>
      <p className="mt-2 text-sm text-ink/65">Fields marked * are required. Email is optional.</p>
      <fieldset disabled={status === "submitting"} className="mt-6 space-y-5 disabled:opacity-70">
        <div>
          <label htmlFor="grievance-name" className="text-sm font-medium text-ink">Full name *</label>
          <input id="grievance-name" name="name" autoComplete="name" required maxLength={150} className={INPUT_CLASS} />
        </div>
        <div>
          <label htmlFor="grievance-phone" className="text-sm font-medium text-ink">Phone number *</label>
          <input id="grievance-phone" name="phone_number" type="tel" autoComplete="tel" required maxLength={15} pattern="[+]?[0-9]{7,15}" title="Enter 7 to 15 digits with an optional leading + (maximum 15 characters total)." className={INPUT_CLASS} />
        </div>
        <div>
          <label htmlFor="grievance-email" className="text-sm font-medium text-ink">Email (optional)</label>
          <input id="grievance-email" name="email" type="email" autoComplete="email" maxLength={254} className={INPUT_CLASS} />
        </div>
        <div>
          <label htmlFor="grievance-subject" className="text-sm font-medium text-ink">Subject *</label>
          <input id="grievance-subject" name="subject" required maxLength={200} placeholder="e.g. Appointment, billing, service or privacy concern" className={INPUT_CLASS} />
        </div>
        <div>
          <label htmlFor="grievance-details" className="text-sm font-medium text-ink">What happened, and how can we help? *</label>
          <textarea id="grievance-details" name="details" required rows={6} maxLength={5000} aria-describedby="grievance-details-help" className={INPUT_CLASS} />
          <p id="grievance-details-help" className="mt-2 text-sm text-ink/65">
            Include relevant dates, a booking/payment reference if available, and the outcome you
            are requesting. Do not include passwords, OTPs, payment PINs, full card details or
            unnecessary medical records. Maximum 5,000 characters.
          </p>
        </div>
        <label className="flex items-start gap-3 text-sm leading-relaxed text-ink/75">
          <input name="consent" type="checkbox" required className="mt-1 h-4 w-4 shrink-0 accent-primary" />
          <span>
            I agree to be contacted about this complaint and acknowledge the{" "}
            <Link href="/privacy" className="font-semibold text-primary-darker underline underline-offset-4">Privacy Policy</Link>. *
          </span>
        </label>
        <button type="submit" className={getButtonClasses("primary", "lg", "w-full disabled:cursor-wait")}>
          {status === "submitting" ? <><Loader2 className="h-5 w-5 animate-spin" /> Submitting...</> : "Submit complaint"}
        </button>
      </fieldset>
      {status === "error" && (
        <div role="alert" className="mt-4 flex items-start gap-2 rounded-xl bg-red-50 p-4 text-sm text-red-700">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          {errorMessage}
        </div>
      )}
    </form>
  );
}
