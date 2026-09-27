"use client";

import { useRef, useState, type ChangeEvent, type FormEvent } from "react";
import {
  AlertCircle,
  Building2,
  CheckCircle2,
  Loader2,
  Upload,
  X,
} from "lucide-react";
import { API_BASE_URL } from "@/lib/api";
import { FlashingBadge } from "../ui/FlashingBadge";

const MAX_FILES = 5;

type Status = "idle" | "submitting" | "success" | "error";

export function HospitalOnboardingForm() {
  const [files, setFiles] = useState<File[]>([]);
  const [status, setStatus] = useState<Status>("idle");
  const [errorMessage, setErrorMessage] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const picked = Array.from(event.target.files ?? []);
    setFiles((prev) => [...prev, ...picked].slice(0, MAX_FILES));
    event.target.value = "";
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setErrorMessage("");

    const form = event.currentTarget;
    const formData = new FormData(form);
    files.forEach((file) => formData.append("documents", file));

    setStatus("submitting");
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/hospitals/applications/`,
        {
          method: "POST",
          body: formData,
        },
      );

      if (!response.ok) {
        throw new Error("Submission failed");
      }

      setStatus("success");
    } catch {
      setStatus("error");
      setErrorMessage(
        "Something went wrong. Please check your details and try again.",
      );
    }
  };

  if (status === "success") {
    return (
      <div className="flex flex-col items-center gap-3 rounded-3xl border border-black/5 bg-primary-light px-6 py-14 text-center">
        <CheckCircle2 className="h-12 w-12 text-primary-darker" />
        <h3 className="font-heading text-xl font-bold text-primary-darker sm:text-2xl">
          You&apos;re in! Priority Partner status locked in 🎉
        </h3>
        <p className="max-w-md text-sm leading-relaxed text-primary-darker/80">
          Our team will reach out before launch. Registration stays completely
          free until we go live — thank you for joining early.
        </p>
      </div>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-6 rounded-3xl border border-black/5 bg-white p-6 shadow-lg shadow-black/[0.03] sm:p-8"
    >
      <div className="flex items-start gap-3 rounded-2xl bg-primary-light px-4 py-3">
        <Building2 className="mt-0.5 h-5 w-5 shrink-0 text-primary-darker" />
        <p className="text-sm font-medium text-primary-darker">
          Launching in 2 months — registration is 100% free till then, and every
          hospital/clinic that signs up now keeps{" "}
          <span className="font-bold">Priority Partner</span> status and gets
          referred patients first at launch.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <label
            htmlFor="facility_name"
            className="text-sm font-medium text-ink/70"
          >
            Hospital / clinic name
          </label>
          <input
            id="facility_name"
            name="facility_name"
            type="text"
            required
            placeholder="e.g. City Care Hospital"
            className="mt-1.5 w-full rounded-xl border border-black/10 bg-white px-4 py-3 text-sm text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
          />
        </div>
        <div>
          <label
            htmlFor="contact_person_name"
            className="text-sm font-medium text-ink/70"
          >
            Contact person
          </label>
          <input
            id="contact_person_name"
            name="contact_person_name"
            type="text"
            required
            placeholder="Owner / administrator name"
            className="mt-1.5 w-full rounded-xl border border-black/10 bg-white px-4 py-3 text-sm text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
          />
        </div>
        <div>
          <label htmlFor="email" className="text-sm font-medium text-ink/70">
            Email
          </label>
          <input
            id="email"
            name="email"
            type="email"
            required
            placeholder="you@example.com"
            className="mt-1.5 w-full rounded-xl border border-black/10 bg-white px-4 py-3 text-sm text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
          />
        </div>
        <div>
          <label
            htmlFor="phone_number"
            className="text-sm font-medium text-ink/70"
          >
            Phone number
          </label>
          <input
            id="phone_number"
            name="phone_number"
            type="tel"
            required
            placeholder="10-digit mobile number"
            className="mt-1.5 w-full rounded-xl border border-black/10 bg-white px-4 py-3 text-sm text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
          />
        </div>
        <div>
          <label htmlFor="city" className="text-sm font-medium text-ink/70">
            City
          </label>
          <input
            id="city"
            name="city"
            type="text"
            required
            placeholder="e.g. Lucknow"
            className="mt-1.5 w-full rounded-xl border border-black/10 bg-white px-4 py-3 text-sm text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
          />
        </div>
        <div>
          <label
            htmlFor="specialties"
            className="text-sm font-medium text-ink/70"
          >
            Specialties (optional)
          </label>
          <input
            id="specialties"
            name="specialties"
            type="text"
            placeholder="e.g. Cardiology, Orthopedics"
            className="mt-1.5 w-full rounded-xl border border-black/10 bg-white px-4 py-3 text-sm text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
          />
        </div>
        <div>
          <label
            htmlFor="bed_count"
            className="text-sm font-medium text-ink/70"
          >
            Number of beds (optional)
          </label>
          <input
            id="bed_count"
            name="bed_count"
            type="number"
            min={0}
            placeholder="e.g. 50"
            className="mt-1.5 w-full rounded-xl border border-black/10 bg-white px-4 py-3 text-sm text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
          />
        </div>
        <div className="sm:col-span-2">
          <label htmlFor="address" className="text-sm font-medium text-ink/70">
            Address (optional)
          </label>
          <input
            id="address"
            name="address"
            type="text"
            placeholder="Street, area, city"
            className="mt-1.5 w-full rounded-xl border border-black/10 bg-white px-4 py-3 text-sm text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
          />
        </div>
      </div>

      <div>
        <label htmlFor="message" className="text-sm font-medium text-ink/70">
          Anything you&apos;d like us to know? (optional)
        </label>
        <textarea
          id="message"
          name="message"
          rows={3}
          placeholder="Registration number, empanelment details, availability, etc."
          className="mt-1.5 w-full resize-none rounded-xl border border-black/10 bg-white px-4 py-3 text-sm text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
        />
      </div>

      <div>
        <p className="text-sm font-medium text-ink/70">
          Upload registration certificate / empanelment proof{" "}
          <span className="text-ink/40">(optional)</span>
        </p>
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={files.length >= MAX_FILES}
          className="mt-2 flex w-full items-center justify-center gap-2 rounded-xl border-2 border-dashed border-primary/30 bg-primary-soft px-4 py-6 text-sm font-medium text-primary-darker/70 transition-colors hover:border-primary/50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Upload className="h-5 w-5" />
          Click to upload (PDF, JPG, PNG — up to {MAX_FILES} files)
        </button>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.jpg,.jpeg,.png"
          onChange={handleFileChange}
          className="hidden"
        />
        {files.length > 0 && (
          <ul className="mt-3 space-y-2">
            {files.map((file, index) => (
              <li
                key={`${file.name}-${index}`}
                className="flex items-center justify-between rounded-lg bg-primary-soft px-3 py-2 text-xs text-ink/70"
              >
                <span className="truncate">{file.name}</span>
                <button
                  type="button"
                  onClick={() => removeFile(index)}
                  aria-label={`Remove ${file.name}`}
                  className="ml-2 shrink-0 text-ink/40 hover:text-ink"
                >
                  <X className="h-4 w-4" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {errorMessage && (
        <div className="flex items-center gap-2 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {errorMessage}
        </div>
      )}
      <FlashingBadge className="sm:hidden">Limited Time Offer</FlashingBadge>
      <div className="relative">
        <FlashingBadge className="absolute -top-4 left-1/2 hidden -translate-x-1/2 sm:inline-flex">
          Limited Time Offer
        </FlashingBadge>
      </div>
      <button
        type="submit"
        disabled={status === "submitting"}
        className="flex w-full items-center justify-center gap-2 rounded-full bg-primary px-6 py-4 text-base font-semibold text-white shadow-lg shadow-primary/25 transition-all hover:bg-primary-dark disabled:cursor-not-allowed disabled:opacity-70"
      >
        {status === "submitting" ? (
          <>
            <Loader2 className="h-5 w-5 animate-spin" /> Submitting...
          </>
        ) : (
          "Register as a Priority Partner — It's Free"
        )}
      </button>
      <p className="text-center text-xs text-ink/40">
        No payment required. We&apos;ll contact you directly before the app
        launches.
      </p>
    </form>
  );
}
