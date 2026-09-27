"use client";

import { useEffect, useState } from "react";
import { animate, useMotionValue } from "framer-motion";
import { Building2, Car, Clock, FlaskConical, Smartphone, Stethoscope, Wallet } from "lucide-react";
import { Container } from "@/components/ui/Container";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { BookConsultationButton } from "@/components/ui/BookConsultationButton";

type CostItem = { icon: typeof Wallet; label: string; amount: number };

type Concern = {
  label: string;
  hospitalItems: CostItem[];
  appItems: CostItem[];
};

const CONCERNS: Concern[] = [
  {
    label: "Common Cold & Fever",
    hospitalItems: [
      { icon: Stethoscope, label: "Doctor consultation", amount: 500 },
      { icon: FlaskConical, label: "Tests they often add", amount: 300 },
      { icon: Wallet, label: "Medicines", amount: 400 },
      { icon: Car, label: "Travel + waiting time", amount: 300 },
    ],
    appItems: [
      { icon: Smartphone, label: "Free app consultation", amount: 0 },
      { icon: Wallet, label: "Home-care essentials", amount: 200 },
    ],
  },
  {
    label: "Stomach / Acidity",
    hospitalItems: [
      { icon: Stethoscope, label: "Doctor consultation", amount: 600 },
      { icon: FlaskConical, label: "Tests they often add", amount: 800 },
      { icon: Wallet, label: "Medicines", amount: 500 },
      { icon: Car, label: "Travel + waiting time", amount: 300 },
    ],
    appItems: [
      { icon: Smartphone, label: "Free app consultation", amount: 0 },
      { icon: Wallet, label: "Home-care essentials", amount: 200 },
    ],
  },
  {
    label: "Skin Allergy / Rash",
    hospitalItems: [
      { icon: Stethoscope, label: "Doctor consultation", amount: 600 },
      { icon: FlaskConical, label: "Tests they often add", amount: 400 },
      { icon: Wallet, label: "Medicines / creams", amount: 400 },
      { icon: Car, label: "Travel + waiting time", amount: 300 },
    ],
    appItems: [
      { icon: Smartphone, label: "Free app consultation", amount: 0 },
      { icon: Wallet, label: "Home-care essentials", amount: 200 },
    ],
  },
  {
    label: "Body Pain / Migraine",
    hospitalItems: [
      { icon: Stethoscope, label: "Doctor consultation", amount: 600 },
      { icon: FlaskConical, label: "Scans they often add", amount: 900 },
      { icon: Wallet, label: "Medicines", amount: 400 },
      { icon: Car, label: "Travel + waiting time", amount: 300 },
    ],
    appItems: [
      { icon: Smartphone, label: "Free app consultation", amount: 0 },
      { icon: Wallet, label: "Home-care essentials", amount: 200 },
    ],
  },
  {
    label: "Minor Cuts & Injury",
    hospitalItems: [
      { icon: Stethoscope, label: "Doctor consultation", amount: 700 },
      { icon: FlaskConical, label: "X-ray \u2018just in case\u2019", amount: 900 },
      { icon: Wallet, label: "Dressing & medicines", amount: 500 },
      { icon: Car, label: "Travel + waiting time", amount: 300 },
    ],
    appItems: [
      { icon: Smartphone, label: "Free app consultation", amount: 0 },
      { icon: Wallet, label: "Home-care essentials", amount: 200 },
    ],
  },
];

function sumItems(items: CostItem[]) {
  return items.reduce((total, item) => total + item.amount, 0);
}

const formatInr = (value: number) => `\u20b9${Math.round(value).toLocaleString("en-IN")}`;

// Smoothly tweens the displayed number whenever `value` changes, instead of jumping instantly.
function useAnimatedNumber(value: number) {
  const motionValue = useMotionValue(value);
  const [display, setDisplay] = useState(value);

  useEffect(() => {
    const controls = animate(motionValue, value, {
      duration: 0.5,
      ease: "easeOut",
      onUpdate: (latest) => setDisplay(Math.round(latest)),
    });
    return () => controls.stop();
  }, [value, motionValue]);

  return display;
}

export function SavingsCalculator() {
  const [concernIndex, setConcernIndex] = useState(0);
  const [visitsPerYear, setVisitsPerYear] = useState(3);

  const concern = CONCERNS[concernIndex];
  const hospitalTotal = sumItems(concern.hospitalItems);
  const appTotal = sumItems(concern.appItems);
  const perVisitSavings = Math.max(hospitalTotal - appTotal, 0);
  const annualSavings = perVisitSavings * visitsPerYear;
  const savingsPercent = hospitalTotal > 0 ? Math.round((perVisitSavings / hospitalTotal) * 100) : 0;

  const animatedPerVisit = useAnimatedNumber(perVisitSavings);
  const animatedAnnual = useAnimatedNumber(annualSavings);

  return (
    <section className="bg-primary-soft py-20 sm:py-28">
      <Container>
        <div className="mx-auto max-w-2xl text-center">
          <Eyebrow>Calculate your savings</Eyebrow>
          <h2 className="mt-5 font-heading text-3xl font-bold tracking-tight text-ink sm:text-4xl">
            See exactly what you save with LalahariHealth
          </h2>
          <p className="mt-4 text-base leading-relaxed text-ink/60 sm:text-lg">
            Pick what&apos;s bothering you and watch the real difference — in rupees and hours —
            between a typical clinic visit and an app consultation.
          </p>
        </div>

        <div className="mt-10 flex flex-wrap justify-center gap-2.5">
          {CONCERNS.map((item, index) => (
            <button
              key={item.label}
              type="button"
              onClick={() => setConcernIndex(index)}
              aria-pressed={index === concernIndex}
              className={
                index === concernIndex
                  ? "rounded-full bg-primary px-5 py-2.5 text-sm font-semibold text-white shadow-md shadow-primary/25"
                  : "rounded-full border-2 border-black/10 bg-white px-5 py-2.5 text-sm font-medium text-ink/70 hover:border-primary/40"
              }
            >
              {item.label}
            </button>
          ))}
        </div>

        <div className="mt-10 grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="rounded-3xl border border-black/5 bg-white p-6 sm:p-8">
            <div className="flex items-center gap-3">
              <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-red-50 text-red-500">
                <Building2 className="h-5 w-5" />
              </span>
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-ink/40">
                  Without LalahariHealth
                </p>
                <h3 className="font-heading text-lg font-bold text-ink">
                  Typical clinic / hospital visit
                </h3>
              </div>
            </div>
            <ul className="mt-6 space-y-4">
              {concern.hospitalItems.map((item) => (
                <li key={item.label} className="flex items-center justify-between text-sm">
                  <span className="flex items-center gap-2.5 text-ink/70">
                    <item.icon className="h-4 w-4 shrink-0 text-ink/40" />
                    {item.label}
                  </span>
                  <span className="shrink-0 font-semibold text-ink">{formatInr(item.amount)}</span>
                </li>
              ))}
            </ul>
            <div className="mt-6 flex items-center justify-between border-t border-black/5 pt-4">
              <span className="font-heading font-semibold text-ink">Estimated total</span>
              <span className="font-heading text-2xl font-extrabold text-ink">
                {formatInr(hospitalTotal)}
              </span>
            </div>
          </div>

          <div className="rounded-3xl border-2 border-primary bg-white p-6 shadow-lg shadow-primary/10 sm:p-8">
            <div className="flex items-center gap-3">
              <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary-light text-primary-darker">
                <Smartphone className="h-5 w-5" />
              </span>
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-primary-darker/70">
                  With LalahariHealth
                </p>
                <h3 className="font-heading text-lg font-bold text-ink">
                  App consultation, from home
                </h3>
              </div>
            </div>
            <ul className="mt-6 space-y-4">
              {concern.appItems.map((item) => (
                <li key={item.label} className="flex items-center justify-between text-sm">
                  <span className="flex items-center gap-2.5 text-ink/70">
                    <item.icon className="h-4 w-4 shrink-0 text-primary" />
                    {item.label}
                  </span>
                  <span className="shrink-0 font-semibold text-ink">{formatInr(item.amount)}</span>
                </li>
              ))}
              <li className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-2.5 text-ink/70">
                  <Car className="h-4 w-4 shrink-0 text-primary" />
                  Travel + waiting time
                </span>
                <span className="shrink-0 font-semibold text-ink">{formatInr(0)}</span>
              </li>
            </ul>
            <div className="mt-6 flex items-center justify-between border-t border-primary/15 pt-4">
              <span className="font-heading font-semibold text-ink">Estimated total</span>
              <span className="font-heading text-2xl font-extrabold text-primary-darker">
                {formatInr(appTotal)}
              </span>
            </div>
          </div>
        </div>

        <div className="mt-10 rounded-3xl bg-gradient-to-br from-primary-darker via-primary-dark to-primary p-6 text-center sm:p-10">
          <label htmlFor="visits-per-year" className="text-sm font-medium text-white/80">
            How many times a year does your family usually need a doctor?
          </label>
          <div className="mx-auto mt-3 flex max-w-md items-center gap-4">
            <input
              id="visits-per-year"
              type="range"
              min={1}
              max={12}
              value={visitsPerYear}
              onChange={(event) => setVisitsPerYear(Number(event.target.value))}
              className="h-2 w-full cursor-pointer appearance-none rounded-full bg-white/25 accent-white"
            />
            <span className="w-16 shrink-0 font-heading text-lg font-bold text-white">
              {visitsPerYear}x
            </span>
          </div>

          <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="rounded-2xl bg-white/10 p-5">
              <p className="text-xs font-semibold uppercase tracking-wide text-white/70">
                You save per visit
              </p>
              <p className="mt-1 font-heading text-3xl font-extrabold text-white">
                {formatInr(animatedPerVisit)}
              </p>
            </div>
            <div className="rounded-2xl bg-white p-5">
              <p className="text-xs font-semibold uppercase tracking-wide text-primary-darker/70">
                You could save this year
              </p>
              <p className="mt-1 font-heading text-3xl font-extrabold text-primary-darker">
                {formatInr(animatedAnnual)}
              </p>
            </div>
          </div>

          <p className="mt-6 inline-flex items-center gap-2 rounded-full bg-white/15 px-4 py-2 text-sm font-semibold text-white">
            <Clock className="h-4 w-4" />
            That&apos;s about {savingsPercent}% less spent, and zero hours lost travelling.
          </p>

          <div className="mt-8">
            <BookConsultationButton variant="white" size="lg">
              Start Saving — Get Your Free Consultation
            </BookConsultationButton>
          </div>
        </div>

        <p className="mt-6 text-center text-xs text-ink/45">
          Figures are illustrative averages for common, minor concerns, meant to show potential
          savings — actual costs vary by case, city and provider. Always follow medical advice for
          your specific condition.
        </p>
      </Container>
    </section>
  );
}
