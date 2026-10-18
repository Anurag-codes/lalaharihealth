import { Container } from "@/components/ui/Container";
import { HomeOfferContent } from "@/components/sections/HomeOfferContent";
import { HomeContactActions } from "@/components/sections/HomeContactActions";
import { SaleVideo } from "@/components/sections/SaleVideo";
import { TrustStats } from "@/components/sections/TrustStats";
import { Hero } from "@/components/sections/Hero";
import { HealthcareStoryVideos } from "@/components/sections/HealthcareVideoStories";
import { MedicalCostAwareness } from "@/components/sections/MedicalCostAwareness";
import { SexualHealth } from "@/components/sections/SexualHealth";
import { DoctorsShowcase } from "@/components/sections/DoctorsShowcase";
import { BookConsultation } from "@/components/sections/BookConsultation";
import { FAQ } from "@/components/sections/FAQ";
import { FinalCta } from "@/components/sections/FinalCta";

export default function Home() {
  return (
    <>
      <section className="relative overflow-hidden py-10 sm:py-14">
        <Container className="grid grid-cols-1 items-center gap-10 lg:grid-cols-2 lg:gap-14">
          <div>
            <HomeOfferContent />
            <HomeContactActions />
          </div>
          <SaleVideo />
        </Container>
      </section>
      <TrustStats />
      <Hero media={<HealthcareStoryVideos />} howItWorksHref="/get-started#how-it-works" />
      <MedicalCostAwareness />
      <SexualHealth />
      <DoctorsShowcase />
      <BookConsultation />
      <FAQ />
      <FinalCta />
    </>
  );
}
