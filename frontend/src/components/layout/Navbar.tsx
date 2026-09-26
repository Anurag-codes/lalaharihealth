"use client";

import { useState } from "react";
import Link from "next/link";
import { HeartPulse, Menu, Phone, X } from "lucide-react";
import { Container } from "@/components/ui/Container";
import { BookConsultationButton } from "@/components/ui/BookConsultationButton";
import { TextSizeControl } from "@/components/layout/TextSizeControl";

const NAV_LINKS = [
  { label: "How It Works", href: "#how-it-works" },
  { label: "Compare Treatments", href: "#compare-treatments" },
  { label: "Hospital Support", href: "#hospital-support" },
  { label: "Stories", href: "#testimonials" },
  { label: "FAQs", href: "#faq" },
];

export function Navbar() {
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 border-b border-black/5 bg-white/85 backdrop-blur-md">
      <Container className="flex h-18 items-center justify-between py-3">
        <Link href="/" className="flex items-center gap-2" onClick={() => setOpen(false)}>
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-white shadow-md shadow-primary/30">
            <HeartPulse className="h-6 w-6" strokeWidth={2.2} />
          </span>
          <span className="font-heading text-lg font-bold tracking-tight text-ink">
            Lalahari<span className="text-primary">Health</span>
          </span>
        </Link>

        <nav className="hidden items-center gap-8 lg:flex">
          {NAV_LINKS.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="text-sm font-medium text-ink/70 transition-colors hover:text-primary-darker"
            >
              {link.label}
            </a>
          ))}
        </nav>

        <div className="hidden items-center gap-4 lg:flex">
          <TextSizeControl />
          <a
            href="tel:+911800000000"
            className="flex items-center gap-2 text-sm font-semibold text-ink/70 hover:text-primary-darker"
          >
            <Phone className="h-4 w-4 text-primary" />
            1800-000-000
          </a>
          <BookConsultationButton size="sm" />
        </div>

        <div className="flex items-center gap-2 lg:hidden">
          <TextSizeControl />
          <button
            type="button"
            aria-label="Toggle menu"
            onClick={() => setOpen((v) => !v)}
            className="flex h-10 w-10 items-center justify-center rounded-lg text-ink"
          >
            {open ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>
      </Container>

      {open && (
        <div className="border-t border-black/5 bg-white lg:hidden">
          <Container className="flex flex-col gap-1 py-4">
            {NAV_LINKS.map((link) => (
              <a
                key={link.href}
                href={link.href}
                onClick={() => setOpen(false)}
                className="rounded-lg px-3 py-3 text-sm font-medium text-ink/80 hover:bg-primary-light hover:text-primary-darker"
              >
                {link.label}
              </a>
            ))}
            <Link
              href="/for-doctors"
              onClick={() => setOpen(false)}
              className="rounded-lg px-3 py-3 text-sm font-medium text-ink/80 hover:bg-primary-light hover:text-primary-darker"
            >
              For Doctors
            </Link>
            <div className="mt-2 flex flex-col gap-3 px-3">
              <a
                href="tel:+911800000000"
                className="flex items-center gap-2 text-sm font-semibold text-ink/70"
              >
                <Phone className="h-4 w-4 text-primary" />
                1800-000-000
              </a>
              <BookConsultationButton
                className="w-full"
                onBeforeOpen={() => setOpen(false)}
              />
            </div>
          </Container>
        </div>
      )}
    </header>
  );
}
