"use client";

import {
  ArrowRight, BadgePercent, CalendarCheck, Check, FileText, ImageIcon, Infinity as InfinityIcon, Moon, Phone,
  ShieldCheck, Video, X,
} from "lucide-react";
import { useBookingModal } from "@/components/booking/BookingModalContext";
import { useSubscriptionPlan, type SubscriptionPlan } from "@/components/pricing/PricingContext";
import { Container } from "@/components/ui/Container";

const CALL_HREF = "tel:+919289668244";

// Image N on the page uses IMAGE_PROMPTS[N - 1]. Generate each, then replace the matching <ImageSlot>.
const IMAGE_PROMPTS = [
  {
    alt: "Smiling young Indian adult on a sofa on a video call with a doctor",
    prompt:
      "Warm, bright photo of a smiling Indian adult in their early 30s relaxing on a living-room sofa, video-calling a friendly doctor on a smartphone. Natural daylight, soft teal and white tones, modern Indian home, candid and relieved expression, shallow depth of field, premium healthcare ad style, 4:5 portrait, no text.",
  },
  {
    alt: "Adult with a fever at night talking to a doctor on the phone",
    prompt:
      "Night-time photo of an Indian adult sitting up in bed wrapped in a blanket with a mild fever, a thermometer on the side table, holding a phone showing a doctor's video call. Calm, reassuring mood, warm bedside lamp light with soft teal accents, realistic, cinematic, 4:3 landscape, no text.",
  },
  {
    alt: "Middle-aged adult checking blood pressure with a doctor on a tablet",
    prompt:
      "Middle-aged Indian adult at a dining table, smiling while consulting a doctor on a tablet, a home blood-pressure monitor on the arm and a glass of water nearby. Soft morning light, teal and white palette, healthy and confident, realistic photography, 4:3 landscape, no text.",
  },
  {
    alt: "Young professional consulting a doctor on a phone during a work break",
    prompt:
      "Young Indian professional in a bright office cafe, taking a quick video consultation with a doctor on a smartphone, relaxed and confident. Clean modern look, teal accents, natural light, realistic photography, 4:3 landscape, no text.",
  },
] as const;

/** Placeholder until the AI images arrive. */
function ImageSlot({ number, className = "" }: { number: number; className?: string }) {
  return (
    <div
      role="img"
      aria-label={IMAGE_PROMPTS[number - 1].alt}
      data-image-prompt={number}
      className={`flex items-center justify-center rounded-3xl bg-gradient-to-br from-primary-light via-white to-primary-soft ring-1 ring-primary/15 ${className}`}
    >
      <ImageIcon className="h-10 w-10 text-primary/30" aria-hidden />
    </div>
  );
}

const PERKS = [
  { icon: InfinityIcon, title: "Unlimited consults", text: "General physician. 365 days." },
  { icon: Moon, title: "Day or night", text: "Book any hour." },
  { icon: Video, title: "From home", text: "Video call. No queues." },
  { icon: FileText, title: "Prescription in app", text: "Always with you." },
];

const MOMENTS = [
  { image: 2, title: "Fever at midnight?", text: "A doctor, from your bed." },
  { image: 3, title: "Regular check-ups?", text: "As often as you need." },
  { image: 4, title: "No time for clinics?", text: "Consult in your break." },
];

function CtaButtons({ dark = false }: { dark?: boolean }) {
  const { open } = useBookingModal();
  return (
    <div className="flex flex-col gap-3 sm:flex-row">
      <button
        type="button"
        onClick={() => open()}
        className={`animate-pulse-ring inline-flex min-h-14 items-center justify-center gap-2 rounded-full px-8 py-4 text-lg font-bold shadow-lg transition active:scale-[0.97] ${
          dark ? "bg-white text-primary-darker hover:bg-white/90" : "bg-primary text-white shadow-primary/25 hover:bg-primary-dark"
        }`}
      >
        Get unlimited plan <ArrowRight className="h-5 w-5" aria-hidden />
      </button>
      <a
        href={CALL_HREF}
        className={`inline-flex min-h-14 items-center justify-center gap-2 rounded-full border-2 px-8 py-4 text-lg font-bold transition ${
          dark ? "border-white text-white hover:bg-white/10" : "border-primary text-primary-darker hover:bg-primary-light"
        }`}
      >
        <Phone className="h-5 w-5" aria-hidden /> Call +91 92896 68244
      </a>
    </div>
  );
}

function PriceCard({ plan }: { plan: SubscriptionPlan | null }) {
  return (
    <div className="relative rounded-3xl border-2 border-accent-warm/60 bg-white p-6 shadow-xl shadow-primary/10 sm:p-8">
      <span className="absolute -top-3.5 left-6 inline-flex items-center gap-1.5 rounded-full bg-accent-warm px-3.5 py-1 text-xs font-extrabold uppercase tracking-wide text-white">
        <BadgePercent className="h-4 w-4" aria-hidden /> Launch price
      </span>
      <p className="mt-2 text-sm font-semibold text-ink/60">1 year · unlimited general physician consults</p>
      {plan ? (
        <>
          <p className="mt-1 font-heading text-5xl font-extrabold tracking-tight text-ink">
            {plan.price}
            <span className="text-lg font-semibold text-ink/50"> /year</span>
          </p>
          <p className="mt-2 text-base font-bold text-primary-darker">Just {plan.perMonth} a month</p>
          <p className="mt-1 text-sm text-ink/60">
            Pays for itself in {plan.visitsToBreakEven} {plan.visitsToBreakEven === 1 ? "visit" : "visits"}.
          </p>
        </>
      ) : (
        <>
          <p className="mt-1 font-heading text-3xl font-extrabold text-ink">Ask for today&apos;s price</p>
          <p className="mt-2 text-sm text-ink/60">Our team will share it on call.</p>
        </>
      )}
    </div>
  );
}

export function SubscriptionLanding() {
  const plan = useSubscriptionPlan();

  return (
    <>
      {/* 1. Hook */}
      <section className="relative overflow-hidden bg-primary-soft py-10 sm:py-16">
        <Container className="grid grid-cols-1 items-center gap-10 lg:grid-cols-2 lg:gap-14">
          <div className="animate-fade-up">
            <span className="inline-flex items-center gap-2 rounded-full bg-accent-warm/15 px-4 py-2 text-sm font-bold text-accent-warm">
              <span className="animate-flash-urgent h-2 w-2 rounded-full bg-accent-warm" aria-hidden />
              Launch offer · join today, lock this price for a year
            </span>
            <h1 className="mt-5 font-heading text-4xl font-extrabold leading-tight tracking-tight text-ink sm:text-5xl">
              Unlimited doctor visits.
              <br />
              <span className="text-primary-darker">One price. Whole year.</span>
            </h1>
            <p className="mt-4 text-lg text-ink/70">Stop paying every time you fall sick.</p>
            <div className="mt-8 max-w-md">
              <PriceCard plan={plan} />
            </div>
            <div className="mt-6">
              <CtaButtons />
            </div>
          </div>
          <ImageSlot number={1} className="aspect-[4/5] w-full" />
        </Container>
      </section>

      {/* 2. The math */}
      <section aria-labelledby="math-title" className="py-12 sm:py-16">
        <Container>
          <h2 id="math-title" className="text-center font-heading text-3xl font-extrabold tracking-tight text-ink sm:text-4xl">
            Do the math.
          </h2>
          <div className="mx-auto mt-8 grid max-w-3xl grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="rounded-3xl border border-ink/10 bg-white p-6">
              <p className="flex items-center gap-2 text-sm font-bold uppercase tracking-wide text-ink/50">
                <X className="h-5 w-5 text-red-500" aria-hidden /> Pay per visit
              </p>
              <p className="mt-3 font-heading text-3xl font-extrabold text-ink/70 line-through decoration-red-500/70">
                {plan ? plan.yearOfMonthlyVisits : "Every visit"}
              </p>
              <p className="mt-1 text-sm text-ink/60">
                {plan ? `1 visit a month × ${plan.perVisit}` : "Pay again. And again."}
              </p>
            </div>
            <div className="rounded-3xl border-2 border-primary bg-primary-light p-6">
              <p className="flex items-center gap-2 text-sm font-bold uppercase tracking-wide text-primary-darker">
                <Check className="h-5 w-5" aria-hidden /> Unlimited plan
              </p>
              <p className="mt-3 font-heading text-3xl font-extrabold text-primary-darker">{plan ? plan.price : "One price"}</p>
              <p className="mt-1 text-sm text-primary-darker/80">Visit as often as you need</p>
            </div>
          </div>
        </Container>
      </section>

      {/* 3. What you get */}
      <section aria-label="What you get" className="bg-gradient-to-r from-primary-darker via-primary-dark to-primary py-12 sm:py-14">
        <Container className="grid grid-cols-2 gap-6 lg:grid-cols-4">
          {PERKS.map(({ icon: Icon, title, text }) => (
            <div key={title} className="text-white">
              <Icon className="h-8 w-8" aria-hidden />
              <p className="mt-3 font-heading text-lg font-bold">{title}</p>
              <p className="text-sm text-white/80">{text}</p>
            </div>
          ))}
        </Container>
      </section>

      {/* 4. Real moments */}
      <section aria-labelledby="moments-title" className="py-12 sm:py-16">
        <Container>
          <h2 id="moments-title" className="text-center font-heading text-3xl font-extrabold tracking-tight text-ink sm:text-4xl">
            Made for real life.
          </h2>
          <div className="mt-8 grid grid-cols-1 gap-6 md:grid-cols-3">
            {MOMENTS.map(({ image, title, text }) => (
              <div key={title}>
                <ImageSlot number={image} className="aspect-[4/3] w-full" />
                <p className="mt-4 font-heading text-xl font-bold text-ink">{title}</p>
                <p className="text-ink/60">{text}</p>
              </div>
            ))}
          </div>
        </Container>
      </section>

      {/* 5. Trust strip */}
      <section aria-label="Why trust us" className="border-y border-ink/10 bg-primary-soft py-6">
        <Container className="flex flex-wrap items-center justify-center gap-x-8 gap-y-3 text-sm font-semibold text-ink/70">
          <span className="inline-flex items-center gap-2"><ShieldCheck className="h-5 w-5 text-primary" aria-hidden /> Verified doctors</span>
          <span className="inline-flex items-center gap-2"><CalendarCheck className="h-5 w-5 text-primary" aria-hidden /> Valid 365 days</span>
          <span className="inline-flex items-center gap-2"><Phone className="h-5 w-5 text-primary" aria-hidden /> Real people on call</span>
        </Container>
      </section>

      {/* 6. Last push */}
      <section className="bg-ink py-14 sm:py-20">
        <Container className="flex flex-col items-center text-center">
          <p className="font-heading text-3xl font-extrabold leading-tight tracking-tight text-white sm:text-5xl">
            Your next doctor visit
            <br />
            <span className="text-primary">could be your last paid one.</span>
          </p>
          <p className="mt-4 text-lg text-white/70">
            {plan ? `${plan.price} for the year. Launch price — don't miss it.` : "Launch price — don't miss it."}
          </p>
          <div className="mt-8">
            <CtaButtons dark />
          </div>
          <p className="mt-6 text-xs text-white/40">
            Covers your own general physician consultations. Specialists and family bookings are charged separately.
          </p>
        </Container>
      </section>
    </>
  );
}
