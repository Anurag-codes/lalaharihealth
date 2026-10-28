import type { Metadata } from "next";
import Link from "next/link";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { Container } from "@/components/ui/Container";
import { Eyebrow } from "@/components/ui/Eyebrow";

export const metadata: Metadata = {
  title: "Refund Policy | LalahariHealth",
  description: "How refund requests for LalahariHealth consultations are submitted and reviewed.",
  alternates: { canonical: "/refunds" },
};

export default function RefundsPage() {
  return (
    <Container className="max-w-3xl py-12 sm:py-20">
      <Breadcrumbs items={[{ label: "Home", href: "/" }, { label: "Refund Policy", href: "/refunds" }]} />
      <div className="mt-6">
        <Eyebrow>Clear rules for paid services</Eyebrow>
      </div>
      <h1 className="mt-5 font-heading text-3xl font-bold text-ink sm:text-4xl">Refund Policy</h1>
      <p className="mt-3 text-sm text-ink/60">Last updated: 18 October 2026</p>

      <div className="mt-8 space-y-8 text-base leading-relaxed text-ink/75 [&_h2]:mb-3 [&_h2]:font-heading [&_h2]:text-xl [&_h2]:font-semibold [&_h2]:text-ink [&_li]:mt-2 [&_a]:font-medium [&_a]:text-primary-darker [&_a]:underline [&_a]:underline-offset-4">
        <section>
          <h2>1. What is free and what is paid</h2>
          <p>
            Registering with LalahariHealth is free. Consultations, including human-assisted
            consultations arranged through our team, are paid services. Free registration does not
            include a free consultation, treatment or lab test, so there is nothing to refund for
            registration itself.
          </p>
        </section>

        <section>
          <h2>2. Fees are confirmed before you book</h2>
          <p>
            The consultation fee is explained and confirmed before you book or pay. Please check the
            fee and the appointment details before you confirm.
          </p>
        </section>

        <section>
          <h2>3. How to request a refund</h2>
          <p>
            If you are not satisfied with a paid service, submit a request through our{" "}
            <Link href="/grievance">Grievance Support page</Link>, or email{" "}
            <a href="mailto:care@lalaharihealth.com">care@lalaharihealth.com</a>. Please include:
          </p>
          <ul className="list-disc pl-6">
            <li>your booking or payment reference;</li>
            <li>the registered phone number or email address;</li>
            <li>what went wrong and what outcome you are asking for.</li>
          </ul>
        </section>

        <section>
          <h2>4. How requests are reviewed</h2>
          <p>
            Our team reviews each request individually and explains any applicable refund terms.
            Submitting a request does not guarantee a refund. We will not ask you for an OTP,
            password or full payment-card details.
          </p>
        </section>

        <section>
          <h2>5. Refund method and timing</h2>
          <p>
            Where a refund is approved, it is returned through the original payment method. Our team
            will confirm the timeline when your request is reviewed.
          </p>
        </section>

        <section>
          <h2>6. Questions</h2>
          <p>
            For questions about this policy, email{" "}
            <a href="mailto:care@lalaharihealth.com">care@lalaharihealth.com</a> with
            &quot;Refund request&quot; in the subject. See also our{" "}
            <Link href="/terms">Terms of Service</Link>.
          </p>
        </section>
      </div>
    </Container>
  );
}
