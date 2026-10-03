"use client";

import { useRef, useState, type ChangeEvent, type FormEvent } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Loader2,
  Sparkles,
  Upload,
  X,
} from "lucide-react";
import { API_BASE_URL } from "@/lib/api";
import { FlashingBadge } from "../ui/FlashingBadge";

const TREATMENT_OPTIONS = [
  { value: "allopathy", label: "Allopathic" },
  // { value: "homeopathy", label: "Homeopathic" },
  // { value: "ayurveda", label: "Ayurvedic" },
  // { value: "unani", label: "Unani" },
  { value: "home_remedy", label: "Naturopathy/Home Remedy" },
];

const MAX_FILES = 5;

type Status = "idle" | "submitting" | "success" | "error";

export function DoctorOnboardingForm() {
  const [systems, setSystems] = useState<string[]>([]);
  const [consultationCategory, setConsultationCategory] = useState("");
  const [consultationFee, setConsultationFee] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [status, setStatus] = useState<Status>("idle");
  const [errorMessage, setErrorMessage] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const toggleSystem = (value: string) => {
    setSystems((prev) =>
      prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value],
    );
  };

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

    if (systems.length === 0) {
      setErrorMessage("Please select at least one treatment category.");
      return;
    }

    const form = event.currentTarget;
    const formData = new FormData(form);
    systems.forEach((system) => formData.append("treatment_systems", system));
    files.forEach((file) => formData.append("documents", file));

    setStatus("submitting");
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/doctors/applications/`,
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
          You&apos;re in! Priority Doctor status locked in 🎉
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
        <Sparkles className="mt-0.5 h-5 w-5 shrink-0 text-primary-darker" />
        <p className="text-sm font-medium text-primary-darker">
          Launching soon — registration is 100% free for first 100 registrations, and every
          doctor who signs up now keeps{" "}
          <span className="font-bold">Priority Doctor</span> status at launch.
        </p>
      </div>

      <div className="rounded-2xl border border-black/5 bg-white p-4 text-sm leading-relaxed text-ink/70">
        <strong className="text-ink">Consultation pricing:</strong> General Physician / General
        Doctor visits are fixed at ₹200. Specialists choose a fee from ₹200 to ₹2,000. The
        platform fee is 25%, and the remaining 75% is transferred within 48 hours after a
        completed consultation and confirmed payment.
      </div>

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
        <div>
          <label
            htmlFor="full_name"
            className="text-sm font-medium text-ink/70"
          >
            Full name
          </label>
          <input
            id="full_name"
            name="full_name"
            type="text"
            required
            placeholder="Dr. Your Name"
            className="mt-1.5 w-full rounded-xl border border-black/10 bg-white px-4 py-3 text-sm text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
          />
        </div>
        <div>
          <label
            htmlFor="specialization"
            className="text-sm font-medium text-ink/70"
          >
            Specialization
          </label>
          <input
            id="specialization"
            name="specialization"
            type="text"
            required
            placeholder="e.g. General Physician"
            className="mt-1.5 w-full rounded-xl border border-black/10 bg-white px-4 py-3 text-sm text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
          />
        </div>
        {/* <div>
          <label htmlFor="email" className="text-sm font-medium text-ink/70">
            Email <span className="text-ink/40">(optional)</span>
          </label>
          <input
            id="email"
            name="email"
            type="email"
            placeholder="you@example.com"
            className="mt-1.5 w-full rounded-xl border border-black/10 bg-white px-4 py-3 text-sm text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
          />
        </div> */}
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
          <label
            htmlFor="qualification"
            className="text-sm font-medium text-ink/70"
          >
            Education / qualification
          </label>
          <input
            id="qualification"
            name="qualification"
            type="text"
            required
            placeholder="e.g. MBBS, MD (Ayurveda), BHMS"
            className="mt-1.5 w-full rounded-xl border border-black/10 bg-white px-4 py-3 text-sm text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
          />
        </div>
        <div>
          <label
            htmlFor="experience_years"
            className="text-sm font-medium text-ink/70"
          >
            Years of experience
          </label>
          <input
            id="experience_years"
            name="experience_years"
            type="number"
            min={0}
            max={70}
            required
            placeholder="e.g. 8"
            className="mt-1.5 w-full rounded-xl border border-black/10 bg-white px-4 py-3 text-sm text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
          />
        </div>
        <div className="sm:col-span-2">
          <label htmlFor="consultation_category" className="text-sm font-medium text-ink/70">
            Consultation category
          </label>
          <select
            id="consultation_category"
            name="consultation_category"
            required
            value={consultationCategory}
            onChange={(event) => {
              setConsultationCategory(event.target.value);
              setConsultationFee(event.target.value === "general" ? "200" : "");
            }}
            className="mt-1.5 w-full rounded-xl border border-black/10 bg-white px-4 py-3 text-sm text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
          >
            <option value="">Choose general doctor or specialist</option>
            <option value="general">General Physician / General Doctor — fixed ₹200</option>
            <option value="specialist">Specialist — choose your consultation fee</option>
          </select>
        </div>
        {consultationCategory === "general" ? (
          <>
            <input type="hidden" name="consultation_fee" value="200" />
            <div className="sm:col-span-2 rounded-xl bg-primary-soft p-4 text-sm text-ink/70">
              General Physician / General Doctor consultation fee is fixed at{" "}
              <strong className="text-primary-darker">₹200</strong>. Your payout after the 25%
              platform fee is <strong className="text-primary-darker">₹150</strong> per completed,
              paid consultation.
            </div>
          </>
        ) : consultationCategory === "specialist" ? (
          <>
            <div className="sm:col-span-2">
              <label htmlFor="consultation_fee" className="text-sm font-medium text-ink/70">
                What consultation fee makes you happy?
              </label>
              <select
                id="consultation_fee"
                name="consultation_fee"
                required
                value={consultationFee}
                onChange={(event) => setConsultationFee(event.target.value)}
                className="mt-1.5 w-full rounded-xl border border-black/10 bg-white px-4 py-3 text-sm text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
              >
                <option value="">Choose a fee</option>
                {Array.from({ length: 19 }, (_, index) => (index + 2) * 100).map((fee) => (
                  <option key={fee} value={fee}>
                    ₹{fee}
                  </option>
                ))}
              </select>
            </div>
            <div className="sm:col-span-2 rounded-xl bg-primary-soft p-4 text-sm leading-relaxed text-ink/70">
              {consultationFee ? (
                <>
                  From ₹{consultationFee}, the 25% platform fee is ₹
                  {Number(consultationFee) * 0.25}; your payout is ₹
                  {Number(consultationFee) * 0.75} per completed, paid consultation.
                </>
              ) : (
                <>A lower fee may feel more accessible to patients and may encourage bookings; a higher fee may mean fewer bookings. Choose a fair sweet spot for your expertise and patients. Booking volume is not guaranteed.</>
              )}
            </div>
          </>
        ) : null}
        <div >
          <label htmlFor="city" className="text-sm font-medium text-ink/70">
            City (optional)
          </label>
          <input
            id="city"
            name="city"
            type="text"
            placeholder="e.g. Lucknow"
            className="mt-1.5 w-full rounded-xl border border-black/10 bg-white px-4 py-3 text-sm text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
          />
        </div>
      </div>

      <div>
        <p className="text-sm font-medium text-ink/70">
          Treatment categories you practice
        </p>
        <div className="mt-2 flex flex-wrap gap-2">
          {TREATMENT_OPTIONS.map((option) => {
            const selected = systems.includes(option.value);
            return (
              <button
                key={option.value}
                type="button"
                onClick={() => toggleSystem(option.value)}
                aria-pressed={selected}
                className={
                  selected
                    ? "rounded-full border-2 border-primary bg-primary-light px-4 py-2 text-sm font-semibold text-primary-darker"
                    : "rounded-full border-2 border-black/10 px-4 py-2 text-sm font-medium text-ink/60 hover:border-primary/40"
                }
              >
                {option.label}
              </button>
            );
          })}
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
          placeholder="Registration number, clinic details, availability, etc."
          className="mt-1.5 w-full resize-none rounded-xl border border-black/10 bg-white px-4 py-3 text-sm text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
        />
      </div>

      <div>
        <p className="text-sm font-medium text-ink/70">
          Upload certificates / degree proof{" "}
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
          "Register as a Priority Doctor — It's Free"
        )}
      </button>
      <p className="text-center text-xs text-ink/40">
        No payment required. We&apos;ll contact you directly before the app
        launches.
      </p>
    </form>
  );
}
