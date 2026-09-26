import { Container } from "@/components/ui/Container";
import { Button } from "@/components/ui/Button";
import { BookConsultationButton } from "@/components/ui/BookConsultationButton";

export function FinalCta() {
  return (
    <section className="py-20 sm:py-24">
      <Container>
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-primary-darker via-primary-dark to-primary px-6 py-14 text-center sm:px-14">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_80%_0%,rgba(255,255,255,0.15),transparent_50%)]" />
          <h2 className="relative font-heading text-3xl font-extrabold text-white sm:text-4xl">
            Don&apos;t guess your treatment. Ask a doctor first.
          </h2>
          <p className="relative mx-auto mt-4 max-w-xl text-base text-white/85 sm:text-lg">
            Get initial symptom-based guidance free on your first app consultation. Prefer personal
            help? A human-assisted consultation is ₹100.
          </p>
          <div className="relative mt-8 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <BookConsultationButton variant="white" size="lg">
              Book Your Consultation
            </BookConsultationButton>
            <Button href="/for-doctors" variant="outline-white" size="lg">
              Join as a Doctor
            </Button>
          </div>
        </div>
      </Container>
    </section>
  );
}
