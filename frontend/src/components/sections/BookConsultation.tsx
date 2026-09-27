"use client";

import { useState, type FormEvent } from "react";
import { AlertCircle, CheckCircle2, Loader2 } from "lucide-react";
import { Container } from "@/components/ui/Container";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { Button } from "@/components/ui/Button";
import { API_BASE_URL } from "@/lib/api";

const PLANS = [
  {
    name: "App consultation",
    price: "FREE",
    text: "Describe your symptoms in the app and receive initial symptom-based guidance.",
  },
  {
    name: "Human-assisted consultation",
    price: "₹100",
    text: "Speak with our executive to get help arranging a personal consultation.",
    highlight: true,
  },
  {
    name: "App launching soon",
    price: "Soon",
    text: "The app will be available on Google Play and the App Store at launch.",
  },
];

type Status = "idle" | "submitting" | "success" | "error";

export function BookConsultation() {
  const [status, setStatus] = useState<Status>("idle");

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
          phone_number: formData.get("phone"),
          message: formData.get("symptom") || "Callback requested from the homepage pricing form.",
        }),
      });
      if (!response.ok) throw new Error("Request failed");
      setStatus("success");
    } catch {
      setStatus("error");
    }
  };

  return (
    <section id="book-consultation" className="scroll-mt-20 py-20 sm:py-28">
      <Container className="grid grid-cols-1 gap-14 lg:grid-cols-2 lg:gap-16">
        <div>
          <Eyebrow>Simple, honest pricing</Eyebrow>
          <h2 className="mt-5 font-heading text-3xl font-bold tracking-tight text-ink sm:text-4xl">
            No hidden costs. Just care.
          </h2>
          <p className="mt-4 text-base leading-relaxed text-ink/60">
            Start with free app-generated symptom guidance. If you prefer personal help from our
            team, a human-assisted consultation is ₹100; the executive will explain and confirm
            the details before you proceed.
          </p>

          <div className="mt-8 space-y-4">
            {PLANS.map((plan) => (
              <div
                key={plan.name}
                className={
                  plan.highlight
                    ? "flex items-center justify-between rounded-2xl border-2 border-primary bg-primary-light p-5"
                    : "flex items-center justify-between rounded-2xl border border-black/5 bg-white p-5"
                }
              >
                <div>
                  <h3 className="font-heading text-base font-semibold text-ink">{plan.name}</h3>
                  <p className="mt-1 max-w-xs text-sm text-ink/60">{plan.text}</p>
                </div>
                <p className="shrink-0 pl-4 font-heading text-2xl font-extrabold text-primary-darker">
                  {plan.price}
                </p>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-3xl border border-black/5 bg-white p-6 shadow-lg shadow-black/[0.03] sm:p-8">
          <h3 className="font-heading text-xl font-bold text-ink">Request a consultation callback</h3>
          <p className="mt-1 text-sm text-ink/60">
            Human-assisted consultation is ₹100. Share your details and our executive will call
            to explain the service and confirm your appointment.
          </p>

          {status === "success" ? (
            <div className="mt-8 flex flex-col items-center gap-3 rounded-2xl bg-primary-light py-10 text-center">
              <CheckCircle2 className="h-10 w-10 text-primary" />
              <p className="font-heading text-lg font-semibold text-primary-darker">
                Thank you! We&apos;ll call you shortly.
              </p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="mt-6 space-y-4">
              <div>
                <label htmlFor="name" className="text-sm font-medium text-ink/70">
                  Full name
                </label>
                <input
                  id="name"
                  name="name"
                  type="text"
                  required
                  placeholder="Your name"
                  className="mt-1.5 w-full rounded-xl border border-black/10 bg-white px-4 py-3 text-sm text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                />
              </div>
              <div>
                <label htmlFor="phone" className="text-sm font-medium text-ink/70">
                  Phone number
                </label>
                <input
                  id="phone"
                  name="phone"
                  type="tel"
                  required
                  placeholder="10-digit mobile number"
                  className="mt-1.5 w-full rounded-xl border border-black/10 bg-white px-4 py-3 text-sm text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                />
              </div>
              <div>
                <label htmlFor="symptom" className="text-sm font-medium text-ink/70">
                  What&apos;s bothering you?
                </label>
                <textarea
                  id="symptom"
                  name="symptom"
                  rows={3}
                  placeholder="e.g. Recurring headache for 3 days"
                  className="mt-1.5 w-full resize-none rounded-xl border border-black/10 bg-white px-4 py-3 text-sm text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                />
              </div>
              <Button type="submit" size="lg" className="w-full">
                {status === "submitting" ? (
                  <>
                    <Loader2 className="h-5 w-5 animate-spin" /> Sending...
                  </>
                ) : (
                  "Request Callback"
                )}
              </Button>
              {status === "error" && (
                <div className="flex items-center gap-2 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  Something went wrong. Please call us instead at 1800-000-000.
                </div>
              )}
              <p className="text-center text-xs text-ink/40">
                By submitting, you agree to be contacted by our care team regarding your query.
              </p>
            </form>
          )}
        </div>
      </Container>
    </section>
  );
}
