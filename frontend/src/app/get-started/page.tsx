import type { Metadata } from "next";
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
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { Container } from "@/components/ui/Container";

export const metadata: Metadata = {
  title: "Get Started | LalahariHealth",
  description: "See how LalahariHealth works, why registration is free, and how we support you with doctor consultations, treatment comparisons and lab tests.",
  alternates: { canonical: "/get-started" },
};

export default function GetStartedPage() {
  return (
    <>
      <HomeOfferPopup />
      <Container className="pt-6">
        <Breadcrumbs items={[{ label: "Home", href: "/" }, { label: "Get Started", href: "/get-started" }]} />
      </Container>
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
