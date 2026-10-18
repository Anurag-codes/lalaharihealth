import { HeartHandshake, Lock, Stethoscope } from "lucide-react";
import { Container } from "@/components/ui/Container";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { BookConsultationButton } from "@/components/ui/BookConsultationButton";

const POINTS = [
  { icon: Stethoscope, text: "Erectile problems, early ejaculation, low desire, infertility & more" },
  { icon: Lock, text: "100% private and confidential" },
  { icon: HeartHandshake, text: "Verified doctors, no judgement" },
];

export function SexualHealth() {
  return (
    <section id="sexual-health" className="scroll-mt-20 bg-primary-soft py-16 sm:py-20">
      <Container className="max-w-4xl text-center">
        <Eyebrow>Sexual health</Eyebrow>
        <h2 className="mt-5 font-heading text-3xl font-bold tracking-tight text-ink sm:text-4xl">
          We also help with sex-related problems
        </h2>
        <p className="mx-auto mt-4 max-w-2xl text-base leading-relaxed text-ink/65 sm:text-lg">
          Don&apos;t hesitate. Consult a doctor privately, for healthy matrimonial life and happy family, from home.
        </p>
        <p className="mt-2 font-devanagari text-lg font-semibold text-primary-darker">
          शर्माएं नहीं, घर बैठे सलाह लें।
        </p>

        <ul className="mt-8 grid grid-cols-1 gap-3 text-left sm:grid-cols-3">
          {POINTS.map(({ icon: Icon, text }) => (
            <li key={text} className="flex items-start gap-3 rounded-2xl border border-black/5 bg-white p-4 text-sm text-ink/75">
              <Icon className="mt-0.5 h-5 w-5 shrink-0 text-primary-darker" />
              {text}
            </li>
          ))}
        </ul>

        <div className="mt-8">
          <BookConsultationButton size="lg">Get yourself register for free</BookConsultationButton>
        </div>
      </Container>
    </section>
  );
}
