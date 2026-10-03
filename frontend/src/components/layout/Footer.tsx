import Link from "next/link";
import { Camera, Globe, HeartPulse, Mail, MapPin, MessageCircle, Phone, Share2 } from "lucide-react";
import { Container } from "@/components/ui/Container";

const FOOTER_LINKS: { title: string; links: { label: string; href: string }[] }[] = [
  {
    title: "Company",
    links: [
      { label: "How It Works", href: "#how-it-works" },
      { label: "Compare Treatments", href: "#compare-treatments" },
      { label: "Hospital Support", href: "#hospital-support" },
      { label: "Patient Stories", href: "#testimonials" },
    ],
  },
  {
    title: "For Doctors",
    links: [
      { label: "Join as a Doctor", href: "/for-doctors" },
      { label: "Verification Process", href: "/for-doctors#verification" },
      { label: "Earnings & Payouts", href: "/for-doctors#earnings" },
    ],
  },
  {
    title: "Legal",
    links: [
      { label: "Privacy Policy", href: "/privacy" },
      { label: "Terms of Service", href: "/terms" },
      { label: "Refund Policy", href: "/refunds" },
      { label: "Medical Disclaimer", href: "/disclaimer" },
    ],
  },
];

export function Footer() {
  return (
    <footer className="border-t border-black/5 bg-primary-soft">
      <Container className="py-14">
        <div className="grid grid-cols-1 gap-10 sm:grid-cols-2 lg:grid-cols-5">
          <div className="lg:col-span-2">
            <Link href="/" className="flex items-center gap-2">
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-white shadow-md shadow-primary/30">
                <HeartPulse className="h-6 w-6" strokeWidth={2.2} />
              </span>
              <span className="font-heading text-lg font-bold tracking-tight text-ink">
                Lalahari<span className="text-primary">Health</span>
              </span>
            </Link>
            <p className="mt-4 max-w-sm text-sm leading-relaxed text-ink/60">
              Expert doctor consultations that compare Allopathic, Homeopathic, Ayurvedic, Unani
              and Home Remedy options — so you only spend on treatment you actually need.
            </p>
            <div className="mt-5 flex items-center gap-3">
              {[Globe, Camera, MessageCircle, Share2].map((Icon, i) => (
                <a
                  key={i}
                  href="#"
                  aria-label="Social link"
                  className="flex h-9 w-9 items-center justify-center rounded-full bg-white text-primary-darker shadow-sm transition-colors hover:bg-primary hover:text-white"
                >
                  <Icon className="h-4 w-4" />
                </a>
              ))}
            </div>
          </div>

          {FOOTER_LINKS.map((col) => (
            <div key={col.title}>
              <h4 className="font-heading text-sm font-semibold text-ink">{col.title}</h4>
              <ul className="mt-4 space-y-3">
                {col.links.map((link) => (
                  <li key={link.label}>
                    <Link
                      href={link.href}
                      className="text-sm text-ink/60 transition-colors hover:text-primary-darker"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}

          <div>
            <h4 className="font-heading text-sm font-semibold text-ink">Talk to Us</h4>
            <ul className="mt-4 space-y-3 text-sm text-ink/60">
              <li className="flex items-center gap-2">
                <Phone className="h-4 w-4 shrink-0 text-primary" /> 1800-000-000
              </li>
              <li className="flex items-center gap-2">
                <Mail className="h-4 w-4 shrink-0 text-primary" /> care@lalaharihealth.com
              </li>
              <li className="flex items-start gap-2">
                <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-primary" /> Serving patients across
                India, online
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-12 flex flex-col items-center gap-4 border-t border-black/5 pt-6 text-xs text-ink/50 sm:flex-row sm:justify-between">
          <p>© {new Date().getFullYear()} LalahariHealth. All rights reserved with Algolog Systems Private Limited.</p>
          <p className="text-center sm:text-right">
            Not a replacement for emergency care. In a medical emergency, call your local
            emergency number immediately.
          </p>
        </div>
      </Container>
    </footer>
  );
}
