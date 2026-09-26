import { BadgePercent, Building2, HandHeart, SearchCheck } from "lucide-react";
import { Container } from "@/components/ui/Container";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { BookConsultationButton } from "@/components/ui/BookConsultationButton";
import { SiteImage } from "@/components/ui/SiteImage";

const FEATURES = [
  {
    icon: SearchCheck,
    title: "The right hospital, not just the nearest one",
    text: "We match you to hospitals that specialise in your exact condition, based on outcomes — not ads.",
  },
  {
    icon: BadgePercent,
    title: "Cheaper than walking in directly",
    text: "Our hospital partnerships mean negotiated rates that are typically lower than standard billing.",
  },
  {
    icon: Building2,
    title: "Wide partner network",
    text: "Multi-specialty and super-specialty hospitals across major cities, pre-vetted for quality care.",
  },
  {
    icon: HandHeart,
    title: "End-to-end support",
    text: "From appointment booking to upfront cost estimates and second opinions — we stay with you.",
  },
];

export function HospitalSupport() {
  return (
    <section id="hospital-support" className="scroll-mt-20 py-20 sm:py-28">
      <Container className="grid grid-cols-1 items-center gap-14 lg:grid-cols-2 lg:gap-16">
        <div>
          <Eyebrow>When allopathic care is really needed</Eyebrow>
          <h2 className="mt-5 font-heading text-3xl font-bold tracking-tight text-ink sm:text-4xl">
            If it truly needs a hospital, we&apos;ll find you the best — and cheapest — one.
          </h2>
          <p className="mt-4 text-base leading-relaxed text-ink/60 sm:text-lg">
            Sometimes allopathic treatment genuinely is the right call. When that happens, our
            doctors don&apos;t just tell you to go to a hospital — we help you choose the right
            one and connect you to partner hospitals offering better rates.
          </p>

          <div className="mt-8 space-y-6">
            {FEATURES.map(({ icon: Icon, title, text }) => (
              <div key={title} className="flex gap-4">
                <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary-light text-primary-darker">
                  <Icon className="h-5 w-5" />
                </span>
                <div>
                  <h3 className="font-heading text-base font-semibold text-ink">{title}</h3>
                  <p className="mt-1 text-sm leading-relaxed text-ink/60">{text}</p>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-9">
            <BookConsultationButton size="lg">Get Hospital Guidance</BookConsultationButton>
          </div>
        </div>

        <div className="space-y-6">
          <SiteImage
            src="/image_4.png"
            alt="A clean, modern hospital consultation room"
            aspect="aspect-[4/3]"
          />
          <div className="rounded-2xl border border-black/5 bg-white p-5 shadow-sm">
            <p className="text-center text-xs font-semibold uppercase tracking-wide text-ink/40">
              Our growing hospital partner network
            </p>
            <div className="mt-4 grid grid-cols-3 gap-4 sm:grid-cols-4">
              {[1, 2, 3, 4].map((i) => (
                <div
                  key={i}
                  className="flex h-12 items-center justify-center rounded-lg border border-dashed border-primary/30 bg-primary-soft text-[10px] font-medium text-primary-darker/60"
                >
                  Logo {i}
                </div>
              ))}
            </div>
          </div>
        </div>
      </Container>
    </section>
  );
}
