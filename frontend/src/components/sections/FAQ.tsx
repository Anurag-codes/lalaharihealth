"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { Container } from "@/components/ui/Container";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { GeneralFee } from "@/components/pricing/PricingContext";

const FAQS = [
  {
    q: "What is free: registration or consultation?",
    a: (
      <>
        Only registration is free. Consultations are paid. Human-assisted consultation through our team is <GeneralFee />; other consultation fees are confirmed before booking. Free registration does not include a free consultation, treatment or lab test.
      </>
    ),
  },
  {
    q: "Do I have to pay before I know the consultation fee?",
    a: "No. The applicable consultation fee will be explained and confirmed before booking. Registration itself is free and does not pay for any consultation.",
  },
  {
    q: "How are your doctors verified?",
    a: "Every doctor's medical registration, degree certificates and identity are checked by our team before they can accept a single patient.",
  },
  {
    q: "Is home remedy advice actually safe?",
    a: (
      <>
        The app can offer initial symptom-based home-care guidance. It is not a doctor diagnosis. If symptoms are severe, worsening, or urgent, seek medical care; you can also request a human-assisted consultation for <GeneralFee />.
      </>
    ),
  },
  {
    q: "What if my condition needs surgery or hospitalisation?",
    a: "Your doctor will refer you to our partner hospital network, help you pick the right specialist hospital, and share upfront, negotiated cost estimates.",
  },
  {
    q: "Can I get a refund if I'm not satisfied?",
    a: "Please submit a complaint through our Grievance Support page or email care@lalaharihealth.com with your booking or payment reference and what went wrong. Our team will review your request and explain any applicable refund terms; submitting a complaint does not guarantee a refund. Never share an OTP, password or full payment-card details.",
  },
  {
    q: "How do I raise a complaint or privacy concern?",
    a: "Use Grievance Support or Privacy Policy in the footer. You can submit a complaint online, email care@lalaharihealth.com, or call our founder on 9818677599. Include a contact number and a brief description so we can follow up. This is not an emergency medical service.",
  },
];

export function FAQ() {
  const [open, setOpen] = useState<number | null>(0);

  return (
    <section id="faq" className="scroll-mt-20 py-20 sm:py-28">
      <Container className="max-w-3xl">
        <div className="text-center">
          <Eyebrow>Questions, answered</Eyebrow>
          <h2 className="mt-5 font-heading text-3xl font-bold tracking-tight text-ink sm:text-4xl">
            Frequently asked questions
          </h2>
        </div>

        <div className="mt-12 space-y-3">
          {FAQS.map((item, index) => {
            const isOpen = open === index;
            return (
              <div
                key={item.q}
                className="overflow-hidden rounded-2xl border border-black/5 bg-white"
              >
                <button
                  type="button"
                  onClick={() => setOpen(isOpen ? null : index)}
                  className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left sm:px-6 sm:py-5"
                  aria-expanded={isOpen}
                >
                  <span className="font-heading text-sm font-semibold text-ink sm:text-base">
                    {item.q}
                  </span>
                  <ChevronDown
                    className={`h-5 w-5 shrink-0 text-primary transition-transform ${
                      isOpen ? "rotate-180" : ""
                    }`}
                  />
                </button>
                {isOpen && (
                  <div className="px-5 pb-5 text-sm leading-relaxed text-ink/60 sm:px-6">
                    {item.a}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </Container>
    </section>
  );
}
