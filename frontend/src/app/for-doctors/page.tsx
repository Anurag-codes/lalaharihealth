import type { Metadata } from "next";
import {
  BadgeCheck,
  CalendarClock,
  IndianRupee,
  Rocket,
  ShieldCheck,
  Users,
  Zap,
} from "lucide-react";
import { Container } from "@/components/ui/Container";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { Button } from "@/components/ui/Button";
import { SiteImage } from "@/components/ui/SiteImage";
import { RegistrationTabs } from "@/components/sections/RegistrationTabs";
import { FlashingBadge } from "@/components/ui/FlashingBadge";
import { RegistrationOfferPopup } from "@/components/sections/RegistrationOfferPopup";

export const metadata: Metadata = {
  title: "For Doctors | LalahariHealth",
  description:
    "Join LalahariHealth as a consulting doctor. Register free before launch and lock in Priority Doctor status.",
};

const BENEFITS = [
  {
    icon: Users,
    title: "Reach more patients",
    text: "Consult patients across India from wherever you are, on your own schedule.",
  },
  {
    icon: IndianRupee,
    title: "Transparent earnings",
    text: "Set your own consultation fee and get paid out reliably, with 20% platform fees.",
  },
  {
    icon: CalendarClock,
    title: "Flexible hours",
    text: "Take consultations part-time or full-time, whenever suits your practice.",
  },
  {
    icon: BadgeCheck,
    title: "Verified badge",
    text: "Complete a simple KYC process to earn patient trust with a verified profile.",
  },
];

const LAUNCH_PERKS = [
  {
    icon: Zap,
    title: "Free registration",
    text: "No fee to register for first 100 registrations.",
  },
  {
    icon: ShieldCheck,
    title: "Priority Doctor status",
    text: "Early registrants get a Priority Doctor badge and top placement from day one.",
  },
  {
    icon: Rocket,
    title: "First access to patients",
    text: "Be among the first doctors patients see when we go live in your city.",
  },
];

export default function ForDoctorsPage() {
  return (
    <>
      <RegistrationOfferPopup />
      <section className="relative overflow-hidden pt-16 pb-20 sm:pt-20">
        <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(circle_at_85%_10%,rgba(0,167,167,0.12),transparent_45%)]" />
        <Container className="grid grid-cols-1 items-center gap-12 lg:grid-cols-2">
          <div>
            <Eyebrow>Golden opportunity for doctors, hospitals, clinics, labs and to earn through online consultation(Free for first 100 registrations).</Eyebrow>
            <Eyebrow>Launching in Dec 2026</Eyebrow>
            <h1 className="mt-5 font-heading text-4xl font-extrabold leading-tight tracking-tight text-ink sm:text-5xl">
              {/* Bring your expertise online.{" "} */}
              <span className="text-primary">Register free today.</span>
            </h1>
            <p className="mt-5 max-w-lg text-base leading-relaxed text-ink/60 sm:text-lg">
              <b>LalahariHealth is an app providing health consultations to people at affordable rates.</b> 
              As of now we are onboarding Allopathic, Naturopathy(Home Remedy) doctors and Institutions.
              Ayurvedic, Unani and Homeopathy doctors are also welcome. 
              <strong className="text-ink">First 100 registrations free.</strong>
            </p>
            <div className="mt-8">
              <div className="relative">
                <FlashingBadge className="absolute -top-4 left-1/8 hidden -translate-x-1/2 sm:inline-flex">
                  Limited Time Offer
                </FlashingBadge>
                <Button href="#apply" size="lg">
                  Register Now
                </Button>
              </div>
            </div>
          </div>
          <SiteImage
            src="/imge_8_9_10.png"
            alt="A doctor consulting patients online from a clinic"
            aspect="aspect-[4/3]"
          />
        </Container>
      </section>

      <section className="bg-gradient-to-br from-primary-darker via-primary-dark to-primary py-14">
        <Container>
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="font-heading text-2xl font-bold text-white sm:text-3xl">
              Why register before launch?
            </h2>
          </div>
          <div className="mt-10 grid grid-cols-1 gap-6 sm:grid-cols-3">
            {LAUNCH_PERKS.map(({ icon: Icon, title, text }) => (
              <div
                key={title}
                className="rounded-2xl bg-white/10 p-6 text-center backdrop-blur-sm"
              >
                <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-white/15 text-white">
                  <Icon className="h-6 w-6" />
                </span>
                <h3 className="mt-4 font-heading text-base font-semibold text-white">
                  {title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-white/80">
                  {text}
                </p>
              </div>
            ))}
          </div>
        </Container>
      </section>

      <section className="bg-primary-soft py-20">
        <Container>
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="font-heading text-3xl font-bold tracking-tight text-ink sm:text-4xl">
              Why join LalahariHealth?
            </h2>
          </div>
          <div className="mt-14 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {BENEFITS.map(({ icon: Icon, title, text }) => (
              <div
                key={title}
                className="rounded-2xl border border-black/5 bg-white p-6"
              >
                <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary-light text-primary-darker">
                  <Icon className="h-6 w-6" />
                </span>
                <h3 className="mt-5 font-heading text-lg font-semibold text-ink">
                  {title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-ink/60">
                  {text}
                </p>
              </div>
            ))}
          </div>
        </Container>
      </section>

      <section id="apply" className="scroll-mt-20 py-20">
        <Container className="max-w-2xl">
          <div className="text-center">
            <Eyebrow>Doctor/Hospital registration</Eyebrow>
            <h2 className="mt-5 font-heading text-3xl font-bold tracking-tight text-ink sm:text-4xl">
              Reserve your Priority Doctor/Hospital status
            </h2>
            <p className="mt-4 text-sm leading-relaxed text-ink/60 sm:text-base">
              Takes about 2 minutes. Document upload is optional — you can add
              it later.
            </p>
          </div>
          <div className="mt-10">
            <RegistrationTabs />
          </div>
        </Container>
      </section>
    </>
  );
}
