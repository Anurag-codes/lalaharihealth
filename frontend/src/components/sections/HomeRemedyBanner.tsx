import { CheckCircle2 } from "lucide-react";
import { Container } from "@/components/ui/Container";
import { BookConsultationButton } from "@/components/ui/BookConsultationButton";
import { SiteImage } from "@/components/ui/SiteImage";

const POINTS = [
  "Doctor-verified remedies using everyday kitchen ingredients",
  "Perfect for minor colds, acidity, headaches, body ache & more",
  "No medicine cost, no side effects, just guided care",
];

export function HomeRemedyBanner() {
  return (
    <section className="relative overflow-hidden bg-gradient-to-br from-primary-darker via-primary-dark to-primary py-20 sm:py-24">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(255,255,255,0.12),transparent_50%)]" />
      <Container className="grid grid-cols-1 items-center gap-12 lg:grid-cols-2">
        <div>
          <p className="font-devanagari text-3xl font-semibold text-white sm:text-4xl">
            घर बैठे इलाज पाओ
          </p>
          <h2 className="mt-3 font-heading text-3xl font-extrabold leading-tight text-white sm:text-4xl">
            Gharelu Ilaaj Ki Salah, Pehli Baar{" "}
            <span className="text-white underline decoration-white/40 decoration-8 underline-offset-4">
              Free
            </span>{" "}
            App Par!
          </h2>
          <p className="mt-5 max-w-lg text-base leading-relaxed text-white/85 sm:text-lg">
            Not every problem needs a pharmacy trip. Describe your symptoms in the app and get
            initial home-care consultation free. For a human-assisted
            consultation, our executive can help for ₹200.
          </p>

          <ul className="mt-7 space-y-3">
            {POINTS.map((point) => (
              <li key={point} className="flex items-start gap-3 text-sm text-white/90 sm:text-base">
                <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-white" />
                {point}
              </li>
            ))}
          </ul>

          <div className="mt-8">
            <BookConsultationButton variant="white" size="lg">
              Get Your App Consultation Free
            </BookConsultationButton>
          </div>
        </div>

        <SiteImage
          src="/image_3.png"
          alt="Home remedy ingredients — ginger, turmeric, honey, tulsi and lemon on a wooden table"
          aspect="aspect-square"
        />
      </Container>
    </section>
  );
}
