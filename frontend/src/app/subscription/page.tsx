import type { Metadata } from "next";
import { SubscriptionLanding } from "@/components/sections/SubscriptionLanding";

export const metadata: Metadata = {
  title: "Unlimited Doctor Consultations for a Year | LalahariHealth",
  description: "One yearly price, unlimited online doctor consultations for you. Book any hour, from home. Launch price.",
  alternates: { canonical: "/subscription" },
};

export default function SubscriptionPage() {
  return <SubscriptionLanding />;
}
