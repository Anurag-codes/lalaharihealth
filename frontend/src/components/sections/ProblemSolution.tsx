import { AlertCircle, HelpCircle, IndianRupee, ShieldQuestion } from "lucide-react";
import { Container } from "@/components/ui/Container";
import { Eyebrow } from "@/components/ui/Eyebrow";

const PAIN_POINTS = [
  {
    icon: HelpCircle,
    title: "Don't know who to trust",
    text: "Random Google searches, conflicting advice from relatives — and no one qualified to ask.",
  },
  {
    icon: IndianRupee,
    title: "Scared of the bill",
    text: "Worried a small problem will turn into lakhs of rupees in tests, medicines and hospital stays.",
  },
  {
    icon: ShieldQuestion,
    title: "Too many options, no guidance",
    text: "Allopathy, Ayurveda, Homeopathy, Unani, home remedies — nobody compares them for you.",
  },
  {
    icon: AlertCircle,
    title: "Surgery? No idea where to go",
    text: "When it truly is serious, finding the right, affordable hospital feels like a full-time job.",
  },
];

export function ProblemSolution() {
  return (
    <section className="py-20 sm:py-28">
      <Container>
        <div className="mx-auto max-w-2xl text-center">
          <Eyebrow>The problem</Eyebrow>
          <h2 className="mt-5 font-heading text-3xl font-bold tracking-tight text-ink sm:text-4xl">
            Sounds familiar?
          </h2>
          <p className="mt-4 text-base leading-relaxed text-ink/60 sm:text-lg">
            Every day, thousands of people either ignore symptoms until it&apos;s serious, or
            rush into expensive treatment they didn&apos;t need to.
          </p>
        </div>

        <div className="mt-14 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {PAIN_POINTS.map(({ icon: Icon, title, text }) => (
            <div
              key={title}
              className="rounded-2xl border border-black/5 bg-white p-6 shadow-sm shadow-black/[0.02] transition-shadow hover:shadow-md"
            >
              <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-red-50 text-red-500">
                <Icon className="h-6 w-6" />
              </span>
              <h3 className="mt-5 font-heading text-lg font-semibold text-ink">{title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink/60">{text}</p>
            </div>
          ))}
        </div>

        <div className="mx-auto mt-14 flex max-w-xl flex-col items-center gap-2 rounded-2xl bg-primary-light px-6 py-5 text-center">
          <p className="font-heading text-lg font-semibold text-primary-darker">
            There&apos;s a simpler, cheaper way to decide. ↓
          </p>
        </div>
      </Container>
    </section>
  );
}
