import { AlertTriangle, CircleHelp, PlayCircle } from "lucide-react";
import { Container } from "@/components/ui/Container";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { BookConsultationButton } from "@/components/ui/BookConsultationButton";
import { BlogSection } from "@/components/sections/BlogSection";

const VIDEO_FILE = "patient-treatment-cost-story.mp4";

export function MedicalCostAwareness() {
  return (
    <section id="medical-cost-awareness" className="scroll-mt-24 bg-white py-20 sm:py-28">
      <Container>
        {/* <div className="mx-auto max-w-3xl text-center">
          <Eyebrow>Understand before a major decision</Eyebrow>
          <h2 className="mt-5 font-heading text-3xl font-bold tracking-tight text-ink sm:text-4xl">
            Tests, procedures and hospital bills can change a family&apos;s finances
          </h2>
          <p className="mt-4 text-base leading-relaxed text-ink/65 sm:text-lg">
            Medical terms and a long estimate can feel overwhelming. You have the right to ask
            what each planned test or procedure is for, what it may cost, and what benefits, risks
            or alternatives to discuss.
          </p>
        </div> */}

        {/* <div className="mt-12 grid grid-cols-1 items-start gap-8 lg:grid-cols-2 lg:gap-12">
          <div>
            <div className="flex items-center gap-3">
              <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary-light text-primary-darker">
                <PlayCircle className="h-6 w-6" />
              </span>
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-primary-darker/70">
                  Patient cost-awareness video
                </p>
                <h3 className="font-heading text-lg font-bold text-ink">Hear the story and ask questions</h3>
              </div>
            </div>

            <video
              className="mt-5 aspect-video w-full rounded-2xl bg-ink object-cover"
              controls
              playsInline
              preload="metadata"
              poster="/image_4.png"
              aria-label="Patient story about medical treatment costs"
            >
              <source src={`/videos/${VIDEO_FILE}`} type="video/mp4" />
              Your browser does not support HTML video.
            </video>
            <p className="mt-3 text-xs leading-relaxed text-ink/50">
              A patient&apos;s experience can help raise questions, but it cannot determine whether
              a test or procedure is appropriate for another person.
            </p>
          </div>

          <div className="rounded-2xl border border-primary/15 bg-primary-soft p-6 sm:p-8">
            <div className="flex items-center gap-3">
              <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-white text-primary-darker">
                <CircleHelp className="h-6 w-6" />
              </span>
              <h3 className="font-heading text-xl font-bold text-ink">Questions to ask before planned care</h3>
            </div>
            <ul className="mt-5 space-y-3 text-sm leading-relaxed text-ink/75 sm:text-base">
              <li>For a planned stent or angioplasty, what diagnosis and test findings support it?</li>
              <li>How urgent is it, and is there time to get another cardiologist&apos;s opinion?</li>
              <li>What are the expected benefits, risks, side effects and alternatives?</li>
              <li>Can I get an itemized estimate, including follow-up care and medicines?</li>
            </ul>
            <div className="mt-5 flex items-start gap-3 rounded-xl bg-amber-50 p-4 text-sm leading-relaxed text-amber-900">
              <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
              Never delay emergency care or stop prescribed treatment based on an online video or
              app response. For a planned, non-emergency procedure, ask your clinician whether a
              second opinion is appropriate.
            </div>
            <div className="mt-6">
              <BookConsultationButton size="lg" className="w-full">
                get yourself register for free
              </BookConsultationButton>
            </div>
          </div>
        </div> */}

        <BlogSection />
      </Container>
    </section>
  );
}