"use client";

import Link from "next/link";
import { ArrowRight, Infinity as InfinityIcon } from "lucide-react";
import { useSubscriptionPlan } from "@/components/pricing/PricingContext";
import { Container } from "@/components/ui/Container";

export function SubscriptionTeaser() {
  const plan = useSubscriptionPlan();

  return (
    <section aria-label="Unlimited consultation plan" className="py-8 sm:py-10">
      <Container>
        <Link
          href="/subscription"
          className="group flex flex-col items-start gap-5 rounded-3xl bg-ink p-6 text-white shadow-xl transition hover:-translate-y-0.5 sm:flex-row sm:items-center sm:justify-between sm:p-8"
        >
          <div className="flex items-center gap-4">
            <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-primary">
              <InfinityIcon className="h-8 w-8" aria-hidden />
            </span>
            <div>
              <p className="text-xs font-extrabold uppercase tracking-wide text-accent-warm">New · Launch price</p>
              <p className="font-heading text-2xl font-extrabold tracking-tight sm:text-3xl">
                Unlimited consultations for a year
              </p>
              <p className="text-white/70">{plan ? `${plan.price}/year · just ${plan.perMonth} a month` : "One price. Whole year."}</p>
            </div>
          </div>
          <span className="inline-flex shrink-0 items-center gap-2 rounded-full bg-white px-6 py-3 font-bold text-primary-darker group-hover:bg-white/90">
            See the plan <ArrowRight className="h-5 w-5" aria-hidden />
          </span>
        </Link>
      </Container>
    </section>
  );
}
