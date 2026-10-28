import type { Metadata } from "next";
import Link from "next/link";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { Container } from "@/components/ui/Container";
import { Eyebrow } from "@/components/ui/Eyebrow";

export const metadata: Metadata = {
  title: "Medical Disclaimer | LalahariHealth",
  description: "What LalahariHealth information and services are, and what they are not, including emergency guidance.",
  alternates: { canonical: "/disclaimer" },
};

export default function DisclaimerPage() {
  return (
    <Container className="max-w-3xl py-12 sm:py-20">
      <Breadcrumbs items={[{ label: "Home", href: "/" }, { label: "Medical Disclaimer", href: "/disclaimer" }]} />
      <div className="mt-6">
        <Eyebrow>Read this before you rely on our content</Eyebrow>
      </div>
      <h1 className="mt-5 font-heading text-3xl font-bold text-ink sm:text-4xl">Medical Disclaimer</h1>
      <p className="mt-3 text-sm text-ink/60">Last updated: 18 October 2026</p>

      <div className="mt-8 space-y-8 text-base leading-relaxed text-ink/75 [&_h2]:mb-3 [&_h2]:font-heading [&_h2]:text-xl [&_h2]:font-semibold [&_h2]:text-ink [&_li]:mt-2 [&_a]:font-medium [&_a]:text-primary-darker [&_a]:underline [&_a]:underline-offset-4">
        <section>
          <h2>1. Information, not diagnosis</h2>
          <p>
            The content on this website, including articles, videos, comparisons of treatment
            options and symptom-based home-care guidance, is for general information only. It is
            not a medical diagnosis and does not replace advice from a qualified doctor who knows
            your health history.
          </p>
        </section>

        <section>
          <h2>2. Not for emergencies</h2>
          <p>
            Do not use this website for a medical emergency. If you have severe, worsening or urgent
            symptoms, call your local emergency number immediately (in India, 112) or go to the
            nearest hospital.
          </p>
        </section>

        <section>
          <h2>3. Do not delay or change treatment on your own</h2>
          <p>
            Do not delay seeing a doctor, and do not stop or change prescribed medicines, because
            of anything you read or watch here. Discuss home remedies, medicines and lab tests with
            your doctor before you use them, especially if you are pregnant, breastfeeding, have a
            long-term condition or take other medicines.
          </p>
        </section>

        <section>
          <h2>4. Independent doctors and providers</h2>
          <p>
            Doctors and healthcare providers listed on or connected through LalahariHealth are
            independent professionals. They are responsible for the advice they give you. We do not
            guarantee any particular result from a consultation, treatment or lab test.
          </p>
        </section>

        <section>
          <h2>5. Lab tests and comparisons</h2>
          <p>
            Information about lab tests, treatment options and cost savings is provided to help you
            make informed choices. It is not a recommendation for you personally. Ask your doctor
            which tests and treatments are right for your situation.
          </p>
        </section>

        <section>
          <h2>6. Questions</h2>
          <p>
            For questions about our content or services, see our{" "}
            <Link href="/terms">Terms of Service</Link> or contact{" "}
            <a href="mailto:care@lalaharihealth.com">care@lalaharihealth.com</a>.
          </p>
        </section>
      </div>
    </Container>
  );
}
