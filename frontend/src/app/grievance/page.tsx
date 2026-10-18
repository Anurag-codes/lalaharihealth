import type { Metadata } from "next";
import { Container } from "@/components/ui/Container";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { GrievanceForm } from "@/components/sections/GrievanceForm";

export const metadata: Metadata = {
  title: "Grievance Support | LalahariHealth",
  description: "Report a service, booking, billing or privacy concern to LalahariHealth.",
};

export default function GrievancePage() {
  return (
    <Container className="py-12 sm:py-20">
      <div className="max-w-3xl">
        <Eyebrow>We are here to listen</Eyebrow>
        <h1 className="mt-5 font-heading text-3xl font-bold text-ink sm:text-4xl">Grievance Support</h1>
        <p className="mt-4 text-base leading-relaxed text-ink/75 sm:text-lg">
          If something went wrong with a booking, consultation, payment, registration or the way
          your information was handled, tell us about it. You can submit a complaint below or
          contact us directly.
        </p>
      </div>

      <div className="mt-10 grid items-start gap-8 lg:grid-cols-2 lg:gap-12">
        <div className="space-y-6">
          <section className="rounded-2xl bg-primary-soft p-6">
            <h2 className="font-heading text-xl font-semibold text-ink">Contact support</h2>
            <dl className="mt-4 space-y-4 text-ink/75">
              <div>
                <dt className="text-sm font-semibold text-ink">Email</dt>
                <dd><a href="mailto:care@lalaharihealth.com" className="break-all text-primary-darker underline underline-offset-4">care@lalaharihealth.com</a></dd>
              </div>
              <div>
                <dt className="text-sm font-semibold text-ink">Founder contact / escalation</dt>
                <dd><a href="tel:+919818677599" className="text-primary-darker underline underline-offset-4">9818677599</a></dd>
              </div>
              <div>
                <dt className="text-sm font-semibold text-ink">Operator</dt>
                <dd>Algolog Systems Private Limited</dd>
              </div>
            </dl>
          </section>
          <section className="text-base leading-relaxed text-ink/75">
            <h2 className="font-heading text-xl font-semibold text-ink">What happens next?</h2>
            <ol className="mt-4 list-decimal space-y-3 pl-6">
              <li>A successfully submitted complaint is saved for review and given a reference number.</li>
              <li>Our team reviews what happened and may contact you for clarification.</li>
              <li>We will explain the outcome or next steps. If your concern remains unresolved, contact our founder with your reference number.</li>
            </ol>
            <p className="mt-4 text-sm">
              A complaint does not automatically confirm a refund or a particular resolution.
              If you cannot submit the form, email or call us using the details above.
            </p>
          </section>
          <p className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm leading-relaxed text-amber-900">
            This support channel is not monitored as an emergency medical service.
            For urgent or worsening symptoms, seek immediate medical care or contact local
            emergency services. Do not wait for a complaint response.
          </p>
        </div>
        <GrievanceForm />
      </div>
    </Container>
  );
}
