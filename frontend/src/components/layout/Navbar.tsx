"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { HeartPulse, Menu, Phone, X } from "lucide-react";
import { Container } from "@/components/ui/Container";
import { BookConsultationButton } from "@/components/ui/BookConsultationButton";
import { getButtonClasses } from "@/components/ui/Button";
import { TextSizeControl } from "@/components/layout/TextSizeControl";

const NAV_LINKS = [
  { label: "How It Works", href: "/get-started#how-it-works" },
  { label: "Hospital Support", href: "/get-started#hospital-support" },
  { label: "Stories", href: "/get-started#testimonials" },
  { label: "Doctors", href: "/#doctors" },
  { label: "FAQs", href: "/#faq" },
  { label: "Blogs", href: "/blogs" },
];

export function Navbar() {
  const [open, setOpen] = useState(false);
  const onDoctorsPage = usePathname() === "/for-doctors";
  const registerLabel = "Get yourself register for free";

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

        <nav className="hidden items-center gap-4 xl:flex">
          {NAV_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="text-sm font-medium text-ink/70 transition-colors hover:text-primary-darker"
            >
              {link.label}
            </Link>
          ))}
        </nav>

        <div className="hidden items-center gap-4 xl:flex">
          <TextSizeControl />
          <a
            href="tel:+911800000000"
            className="flex items-center gap-2 text-sm font-semibold text-ink/70 hover:text-primary-darker"
          >
            <Phone className="h-4 w-4 text-primary" />
            1800-000-000
          </a>
          {onDoctorsPage ? (
            <a href="#apply" className={getButtonClasses("primary", "sm")}>
              {registerLabel}
            </a>
          ) : (
            <BookConsultationButton size="sm">{registerLabel}</BookConsultationButton>
          )}
        </div>

        <div className="flex items-center gap-2 xl:hidden">
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
        <div className="border-t border-black/5 bg-white xl:hidden">
          <Container className="flex flex-col gap-1 py-4">
            {NAV_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setOpen(false)}
                className="rounded-lg px-3 py-3 text-sm font-medium text-ink/80 hover:bg-primary-light hover:text-primary-darker"
              >
                {link.label}
              </Link>
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
              {onDoctorsPage ? (
                <a
                  href="#apply"
                  onClick={() => setOpen(false)}
                  className={getButtonClasses("primary", "md", "w-full")}
                >
                  {registerLabel}
                </a>
              ) : (
                <BookConsultationButton
                  size="md"
                  className="w-full"
                  onBeforeOpen={() => setOpen(false)}
                >
                  {registerLabel}
                </BookConsultationButton>
              )}
            </div>
          </Container>
        </div>
      )}
    </header>
  );
}
