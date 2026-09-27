import { Container } from "@/components/ui/Container";
import { Button } from "@/components/ui/Button";
import { BookConsultationButton } from "@/components/ui/BookConsultationButton";
import { FlashingBadge } from "@/components/ui/FlashingBadge";

export function FinalCta() {
  return (
    <section className="py-20 sm:py-24">
      <Container>
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-primary-darker via-primary-dark to-primary px-6 py-14 text-center sm:px-14">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_80%_0%,rgba(255,255,255,0.15),transparent_50%)]" />
          <h2 className="relative font-heading text-3xl font-extrabold text-white sm:text-4xl">
            Don&apos;t sell your property or take heavy loans for treatment. Ask a doctor first.
          </h2>
          <p className="relative mx-auto mt-4 max-w-xl text-base text-white/85 sm:text-lg">
            Get initial symptom-based consultation free on your app. Download the app now!
          </p>
          <div className="relative mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <FlashingBadge className="sm:hidden">Limited Time Offer</FlashingBadge>
            <div className="relative">
              <FlashingBadge className="absolute -top-4 left-1/2 hidden -translate-x-1/2 sm:inline-flex">
                Limited Time Offer
              </FlashingBadge>
              <BookConsultationButton variant="white" size="lg">
                Book Your Free Consultation
              </BookConsultationButton>
            </div>
            <Button href="/for-doctors" variant="outline-white" size="lg">
              Join as a Priority doctor/medical center
            </Button>
          </div>
        </div>
      </Container>
    </section>
  );
}
