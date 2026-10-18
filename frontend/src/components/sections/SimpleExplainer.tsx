import { Phone, ShieldCheck } from "lucide-react";
import { Container } from "@/components/ui/Container";
import { BookConsultationButton } from "@/components/ui/BookConsultationButton";
import { GeneralFee } from "@/components/pricing/PricingContext";

// Plain-language explainer aimed at first-time and elderly visitors who may
// skip past the flashier Hero section — one idea per line, one obvious action.
export function SimpleExplainer() {
  return (
    <section className="border-y border-black/5 bg-primary-soft py-14 sm:py-16">
      <Container className="max-w-3xl text-center">
        <span className="inline-flex h-14 w-14 items-center justify-center rounded-full bg-primary text-white">
          <ShieldCheck className="h-7 w-7" />
        </span>

        <h2 className="mt-5 font-heading text-2xl font-bold text-ink sm:text-3xl">
          What is LalahariHealth?
        </h2>

        <p className="mt-4 text-lg leading-relaxed text-ink/80 sm:text-xl">
          Register for free and explore consultation options for your health problem.
          Our team can arrange a human-assisted consultation for <GeneralFee />.
          Other consultation fees are confirmed before booking.
        </p>

        <p className="font-devanagari mt-3 text-base leading-relaxed text-ink/60 sm:text-lg">
          आसान भाषा में: पंजीकरण मुफ़्त है, परामर्श नहीं। हमारी टीम <GeneralFee /> में परामर्श की व्यवस्था करेगी।
          अन्य परामर्श शुल्क बुकिंग से पहले बताए जाएंगे।
        </p>

        <p className="mt-6 text-base font-semibold text-ink sm:text-lg">
          App-based guidance is not a doctor diagnosis. For urgent symptoms, seek medical care.
        </p>

        <div className="mt-6 flex flex-col items-center gap-3">
          <BookConsultationButton size="lg" className="w-full max-w-sm sm:w-auto">
            <Phone className="h-5 w-5" />
            Book Consultation — Talk to Us
          </BookConsultationButton>
          <p className="text-sm text-ink/60">
            Registration is free. Request a human-assisted consultation for <GeneralFee />,
            or confirm other consultation fees before booking.
          </p>
        </div>
      </Container>
    </section>
  );
}
