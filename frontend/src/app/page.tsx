import { Hero } from "@/components/sections/Hero";
import { SimpleExplainer } from "@/components/sections/SimpleExplainer";
import { TrustStats } from "@/components/sections/TrustStats";
import { ProblemSolution } from "@/components/sections/ProblemSolution";
import { HowItWorks } from "@/components/sections/HowItWorks";
import { TreatmentComparison } from "@/components/sections/TreatmentComparison";
import { MedicalCostAwareness } from "@/components/sections/MedicalCostAwareness";
import { HomeRemedyBanner } from "@/components/sections/HomeRemedyBanner";
import { HospitalSupport } from "@/components/sections/HospitalSupport";
import { WhyChooseUs } from "@/components/sections/WhyChooseUs";
import { VideoTestimonials } from "@/components/sections/VideoTestimonials";
import { DoctorsShowcase } from "@/components/sections/DoctorsShowcase";
import { BookConsultation } from "@/components/sections/BookConsultation";
import { FAQ } from "@/components/sections/FAQ";
import { FinalCta } from "@/components/sections/FinalCta";
import { HomeOfferPopup } from "@/components/sections/HomeOfferPopup";
import { HomeCallVideo } from "@/components/sections/HomeCallVideo";

export default function Home() {
  return (
    <>
      <HomeOfferPopup />
      <HomeCallVideo />
      <Hero />
      <MedicalCostAwareness />
      <TrustStats />
      <ProblemSolution />
      <HowItWorks />
      <TreatmentComparison />
      <HomeRemedyBanner />
      <HospitalSupport />
      <WhyChooseUs />
      <VideoTestimonials />
      <SimpleExplainer />
      <DoctorsShowcase />
      <BookConsultation />
      <FAQ />
      <FinalCta />
    </>
  );
}
