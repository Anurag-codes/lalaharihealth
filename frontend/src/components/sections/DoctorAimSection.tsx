"use client";

import { useEffect, useState, type ReactNode } from "react";
import {
  ArrowRight,
  BadgeCheck,
  CalendarClock,
  FlaskConical,
  Hospital,
  House,
  IndianRupee,
  Layers,
  PiggyBank,
  Rocket,
  Scale,
  Smartphone,
  Stethoscope,
  Users,
  Video,
  type LucideIcon,
} from "lucide-react";
import { Container } from "@/components/ui/Container";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { GeneralFee } from "@/components/pricing/PricingContext";

type Point = { icon: LucideIcon; title: string; text: ReactNode };

const TABS: { id: string; label: string; points: Point[] }[] = [
  {
    id: "patients",
    label: "Why patients download",
    points: [
      { icon: House, title: "Care at home", text: "No travel to doctors, labs and hospitals." },
      { icon: PiggyBank, title: "Concessional rates", text: "Consultations, treatment and lab tests." },
      { icon: Scale, title: "Honest comparison", text: "Allopathic and Natural options, side by side." },
      { icon: Hospital, title: "Hospital help", text: "Guided referrals at lower rates." },
    ],
  },
  {
    id: "provide",
    label: "What we provide",
    points: [
      { icon: Stethoscope, title: "Online consultations", text: <>Human-assisted, from <GeneralFee />.</> },
      { icon: FlaskConical, title: "Lab tests at home", text: "At concessional rates." },
      { icon: Layers, title: "Every treatment system", text: "Compared with clear costs." },
      { icon: BadgeCheck, title: "Verified doctors only", text: "Credentials checked before consults." },
    ],
  },
  {
    id: "you",
    label: "What you get",
    points: [
      { icon: Users, title: "Patients come to you", text: "We bring them through the app." },
      { icon: CalendarClock, title: "Your hours", text: "Consult anywhere, part-time or full-time." },
      { icon: IndianRupee, title: "75% of every fee", text: "Paid within 48 hours." },
      { icon: Rocket, title: "Priority badge", text: "Free for the First 20 registrations." },
    ],
  },
];

const FLOW = [
  { icon: Smartphone, label: "Patient books from home" },
  { icon: Users, label: "We match a doctor" },
  { icon: Video, label: "You consult & earn" },
];

const ROTATE_MS = 6000;

export function DoctorAimSection() {
  const [active, setActive] = useState(0);
  const [autoRotate, setAutoRotate] = useState(true);

  useEffect(() => {
    if (!autoRotate || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const timer = window.setInterval(() => setActive((index) => (index + 1) % TABS.length), ROTATE_MS);
    return () => window.clearInterval(timer);
  }, [autoRotate]);

  const selectTab = (index: number) => {
    setAutoRotate(false);
    setActive(index);
  };
  const tab = TABS[active];

  return (
    <section id="our-aim" className="scroll-mt-20 bg-primary-soft py-16 sm:py-20">
      <Container className="max-w-5xl">
        <div className="text-center">
          <Eyebrow>Our aim</Eyebrow>
          <h2 className="mt-4 font-heading text-3xl font-bold tracking-tight text-ink sm:text-4xl">
            Affordable care, <span className="text-primary">at home</span>
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-base text-ink/60 sm:text-lg">
            So no one sells property or takes heavy loans for treatment.
          </p>
        </div>

        <ol className="mx-auto mt-10 flex max-w-3xl items-start justify-between gap-1 sm:gap-3">
          {FLOW.map(({ icon: Icon, label }, index) => (
            <li key={label} className="contents">
              <div className="flex w-24 flex-col items-center text-center sm:w-40">
                <span
                  className="animate-float flex h-14 w-14 items-center justify-center rounded-2xl bg-white text-primary-darker shadow-lg shadow-primary/15 sm:h-16 sm:w-16"
                  style={{ animationDelay: `${index * 0.6}s` }}
                >
                  <Icon className="h-7 w-7" />
                </span>
                <span className="mt-3 text-xs font-semibold leading-snug text-ink sm:text-sm">{label}</span>
              </div>
              {index < FLOW.length - 1 && (
                <ArrowRight aria-hidden className="mt-4 h-6 w-6 shrink-0 text-primary sm:mt-5" />
              )}
            </li>
          ))}
        </ol>

        <div
          role="tablist"
          aria-label="Our aim"
          className="mx-auto mt-12 grid max-w-2xl grid-cols-3 gap-1 rounded-2xl border-2 border-black/5 bg-white p-1.5 sm:rounded-full"
        >
          {TABS.map((item, index) => (
            <button
              key={item.id}
              type="button"
              role="tab"
              id={`aim-tab-${item.id}`}
              aria-selected={index === active}
              aria-controls="aim-panel"
              onClick={() => selectTab(index)}
              className={`rounded-xl px-2 py-2.5 text-xs font-semibold leading-tight transition-colors sm:rounded-full sm:px-4 sm:text-sm ${
                index === active
                  ? "bg-primary text-white shadow-md shadow-primary/25"
                  : "text-ink/60 hover:text-primary-darker"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>

        <div
          key={tab.id}
          id="aim-panel"
          role="tabpanel"
          aria-labelledby={`aim-tab-${tab.id}`}
          className="mt-8 grid grid-cols-2 gap-3 sm:gap-5 lg:grid-cols-4"
        >
          {tab.points.map(({ icon: Icon, title, text }, index) => (
            <div
              key={title}
              className="animate-fade-up group rounded-2xl border border-black/5 bg-white p-4 text-center transition-transform hover:-translate-y-1 hover:shadow-xl hover:shadow-primary/10 sm:p-6"
              style={{ animationDelay: `${index * 80}ms` }}
            >
              <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-primary-light text-primary-darker transition-colors group-hover:bg-primary group-hover:text-white">
                <Icon className="h-6 w-6" />
              </span>
              <h3 className="mt-4 font-heading text-sm font-semibold text-ink sm:text-base">{title}</h3>
              <p className="mt-1 text-xs leading-relaxed text-ink/60 sm:text-sm">{text}</p>
            </div>
          ))}
        </div>

        <div className="mt-6 flex justify-center gap-2" aria-hidden>
          {TABS.map((item, index) => (
            <span
              key={item.id}
              className={`h-1.5 rounded-full transition-all ${index === active ? "w-8 bg-primary" : "w-3 bg-primary/25"}`}
            />
          ))}
        </div>
      </Container>
    </section>
  );
}
