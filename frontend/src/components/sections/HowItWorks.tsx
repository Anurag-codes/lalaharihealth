import { ClipboardList, MessagesSquare, ScanSearch, Sparkles } from "lucide-react";
import { Container } from "@/components/ui/Container";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { VideoPlaceholder } from "@/components/ui/VideoPlaceholder";

const STEPS = [
  {
    icon: ClipboardList,
    title: "Share your symptoms",
    text: "Tell us what's bothering you, in your own words — takes less than 2 minutes.",
  },
  {
    icon: MessagesSquare,
    title: "Get your app guidance free",
    text: "Describe your symptoms in the app to receive initial guidance. Want personal help? An executive can arrange a human-assisted consultation for ₹200.",
  },
  {
    icon: ScanSearch,
    title: "Compare every treatment option",
    text: "See Allopathic, Homeopathic, Ayurvedic, Unani and Home Remedy options side-by-side with honest cost estimates.",
  },
  {
    icon: Sparkles,
    title: "Choose what's right for you",
    text: "Pick the safest, most affordable option. Need a hospital? We'll help you find the best, cheapest one.",
  },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="scroll-mt-20 bg-primary-soft py-20 sm:py-28">
      <Container>
        <div className="mx-auto max-w-2xl text-center">
          <Eyebrow>How it works</Eyebrow>
          <h2 className="mt-5 font-heading text-3xl font-bold tracking-tight text-ink sm:text-4xl">
            From symptom to solution in 4 simple steps
          </h2>
        </div>

        <div className="mt-16 grid grid-cols-1 items-center gap-12 lg:grid-cols-2 lg:gap-16">
          <ol className="space-y-8">
            {STEPS.map(({ icon: Icon, title, text }, index) => (
              <li key={title} className="flex gap-5">
                <div className="flex flex-col items-center">
                  <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-primary text-white shadow-md shadow-primary/30">
                    <Icon className="h-6 w-6" />
                  </span>
                  {index < STEPS.length - 1 && (
                    <span className="mt-2 h-full w-px flex-1 bg-primary/20" />
                  )}
                </div>
                <div className="pb-2">
                  <p className="text-xs font-bold uppercase tracking-wide text-primary-darker">
                    Step {index + 1}
                  </p>
                  <h3 className="mt-1 font-heading text-xl font-semibold text-ink">{title}</h3>
                  <p className="mt-2 max-w-md text-sm leading-relaxed text-ink/60">{text}</p>
                </div>
              </li>
            ))}
          </ol>

          <VideoPlaceholder
            imageSrc="/image_2.png"
          />
        </div>
      </Container>
    </section>
  );
}
