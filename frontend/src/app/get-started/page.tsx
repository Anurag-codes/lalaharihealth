import { Hero } from "@/components/sections/Hero";
import { SimpleExplainer } from "@/components/sections/SimpleExplainer";
import { TrustStats } from "@/components/sections/TrustStats";
import { ProblemSolution } from "@/components/sections/ProblemSolution";
import { HowItWorks } from "@/components/sections/HowItWorks";
import { MedicalCostAwareness } from "@/components/sections/MedicalCostAwareness";
import { HomeRemedyBanner } from "@/components/sections/HomeRemedyBanner";
import { HospitalSupport } from "@/components/sections/HospitalSupport";
import { WhyChooseUs } from "@/components/sections/WhyChooseUs";
import { VideoTestimonials } from "@/components/sections/VideoTestimonials";
import { HomeOfferPopup } from "@/components/sections/HomeOfferPopup";
import { HomeCallVideo } from "@/components/sections/HomeCallVideo";
import { HealthcareVideoStories } from "@/components/sections/HealthcareVideoStories";

export default function GetStartedPage() {
  return (
    <>
      <HomeOfferPopup />
      <HomeCallVideo />
      {/* <Hero />
      <TrustStats />
      <HealthcareVideoStories /> */}
      <MedicalCostAwareness />
      <ProblemSolution />
      <HowItWorks />
      {/* <TreatmentComparison /> */}
      <HomeRemedyBanner />
      <HospitalSupport />
      <WhyChooseUs />
      <VideoTestimonials />
      <SimpleExplainer />
    </>
  );
}
