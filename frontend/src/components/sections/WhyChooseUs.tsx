import { Clock, Lock, ShieldCheck, Sparkles, Stethoscope, Wallet } from "lucide-react";
import { Container } from "@/components/ui/Container";
import { Eyebrow } from "@/components/ui/Eyebrow";

const FEATURES = [
  {
    icon: Stethoscope,
    title: "Verified, experienced doctors",
    text: "Every doctor's registration and credentials are checked before they see a single patient.",
  },
  {
    icon: Wallet,
    title: "Clear, upfront pricing",
    text: "Your app consultation is totally free. No hidden charges. Human-assisted consultation through our team is ₹100.",
  },
  {
    icon: Sparkles,
    title: "Every treatment system, compared",
    text: "Allopathic, Homeopathic, Ayurvedic, Unani and Home Remedy — laid out honestly, side by side.",
  },
  {
    icon: ShieldCheck,
    title: "Hospital assistance when needed",
    text: "Guided referrals to trusted, partner hospitals at negotiated, lower rates.",
  },
  {
    icon: Clock,
    title: "Available when you need it",
    text: "Book a slot that works for you — early morning, late night, or on weekends.",
  },
  {
    icon: Lock,
    title: "Private & secure",
    text: "Your health data and conversations stay confidential — always.",
  },
];

export function WhyChooseUs() {
  return (
    <section className="py-20 sm:py-28">
      <Container>
        <div className="mx-auto max-w-2xl text-center">
          <Eyebrow>Why LalahariHealth</Eyebrow>
          <h2 className="mt-5 font-heading text-3xl font-bold tracking-tight text-ink sm:text-4xl">
            Built around one goal: your trust
          </h2>
        </div>

        <div className="mt-14 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map(({ icon: Icon, title, text }) => (
            <div
              key={title}
              className="rounded-2xl border border-black/5 bg-white p-6 transition-shadow hover:shadow-md"
            >
              <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary-light text-primary-darker">
                <Icon className="h-6 w-6" />
              </span>
              <h3 className="mt-5 font-heading text-lg font-semibold text-ink">{title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink/60">{text}</p>
            </div>
          ))}
        </div>
      </Container>
    </section>
  );
}
