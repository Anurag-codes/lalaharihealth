"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { Container } from "@/components/ui/Container";
import { Eyebrow } from "@/components/ui/Eyebrow";

const FAQS = [
  {
    q: "Is the first app consultation really free?",
    a: "Yes. Your first app consultation provides initial symptom-based guidance at no cost. This is not a doctor diagnosis and does not replace urgent medical care. If you request a human-assisted consultation through our team, the fee is ₹100.",
  },
  {
    q: "How are your doctors verified?",
    a: "Every doctor's medical registration, degree certificates and identity are checked by our team before they can accept a single patient.",
  },
  {
    q: "Is home remedy advice actually safe?",
    a: "The app can offer initial symptom-based home-care guidance. It is not a doctor diagnosis. If symptoms are severe, worsening, or urgent, seek medical care; you can also request a human-assisted consultation for ₹100.",
  },
  {
    q: "What if my condition needs surgery or hospitalisation?",
    a: "Your doctor will refer you to our partner hospital network, help you pick the right specialist hospital, and share upfront, negotiated cost estimates.",
  },
  {
    q: "Can I get a refund if I'm not satisfied?",
    a: "Yes, unresolved consultations are eligible for a refund as per our refund policy — reach out to our support team within 24 hours.",
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
