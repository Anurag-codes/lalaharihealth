import type { Metadata } from "next";
import Link from "next/link";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { Container } from "@/components/ui/Container";
import { Eyebrow } from "@/components/ui/Eyebrow";

export const metadata: Metadata = {
  title: "Terms of Service | LalahariHealth",
  description: "The terms that apply when you use the LalahariHealth website, registration and consultation services.",
  alternates: { canonical: "/terms" },
};

export default function TermsPage() {
  return (
    <Container className="max-w-3xl py-12 sm:py-20">
      <Breadcrumbs items={[{ label: "Home", href: "/" }, { label: "Terms of Service", href: "/terms" }]} />
      <div className="mt-6">
        <Eyebrow>Please read before you use our services</Eyebrow>
      </div>
      <h1 className="mt-5 font-heading text-3xl font-bold text-ink sm:text-4xl">Terms of Service</h1>
      <p className="mt-3 text-sm text-ink/60">Last updated: 18 October 2026</p>

      <div className="mt-8 space-y-8 text-base leading-relaxed text-ink/75 [&_h2]:mb-3 [&_h2]:font-heading [&_h2]:text-xl [&_h2]:font-semibold [&_h2]:text-ink [&_li]:mt-2 [&_a]:font-medium [&_a]:text-primary-darker [&_a]:underline [&_a]:underline-offset-4">
        <section>
          <h2>1. About these terms</h2>
          <p>
            LalahariHealth is operated by Algolog Systems Private Limited. These terms apply when you
            use the LalahariHealth website, register with us, or book a consultation or related
            service. By using these services you agree to these terms. If you do not agree, please
            do not use the services.
          </p>
        </section>

        <section>
          <h2>2. Registration and your account</h2>
          <ul className="list-disc pl-6">
            <li>Registration is free. Registering does not include a free consultation, treatment or lab test.</li>
            <li>You must give accurate information when you register or book, and keep it up to date.</li>
            <li>You are responsible for keeping your login details and one-time passwords (OTPs) private. Do not share them with anyone, including people who say they work for LalahariHealth.</li>
          </ul>
        </section>

        <section>
          <h2>3. Consultations and fees</h2>
          <ul className="list-disc pl-6">
            <li>Consultations are paid services. The fee that applies to a consultation is shown or confirmed before you book.</li>
            <li>Our team will explain the next steps, appointment details and payment before any consultation is confirmed.</li>
            <li>Our service connects you with doctors and healthcare providers. Each doctor or provider is responsible for the medical advice they give.</li>
            <li>Refunds are handled under our <Link href="/refunds">Refund Policy</Link>.</li>
          </ul>
        </section>

        <section>
          <h2>4. Not a substitute for emergency care</h2>
          <p>
            LalahariHealth is not an emergency service. If you think you are having a medical
            emergency, call your local emergency number immediately (in India, 112). Read our{" "}
            <Link href="/disclaimer">Medical Disclaimer</Link> for more information on what our
            content and services can and cannot do.
          </p>
        </section>

        <section>
          <h2>5. Acceptable use</h2>
          <p>You agree not to:</p>
          <ul className="list-disc pl-6">
            <li>give false information, or register or book on someone else&apos;s behalf without permission;</li>
            <li>misuse the website, interfere with its operation, or attempt to access data that is not yours;</li>
            <li>copy, scrape or resell our content or doctor information without written permission.</li>
          </ul>
        </section>

        <section>
          <h2>6. Content on this website</h2>
          <p>
            Text, images, videos and other material on this website belong to LalahariHealth or
            the people or organisations credited with them. Third-party videos and articles are
            shared for information only and do not mean we endorse their views.
          </p>
        </section>

        <section>
          <h2>7. Limitation of responsibility</h2>
          <p>
            We work to keep our services accurate and available, but we do not guarantee any
            particular medical outcome, and our services are not a substitute for in-person care.
            To the extent permitted by law, LalahariHealth is not liable for indirect losses arising
            from your use of the website or from the advice given by independent doctors.
          </p>
        </section>

        <section>
          <h2>8. Governing law</h2>
          <p>
            These terms are governed by the laws of India. Any dispute will be subject to the
            jurisdiction of the courts in India.
          </p>
        </section>

        <section>
          <h2>9. Changes to these terms and contact</h2>
          <p>
            We may update these terms. The date above shows the latest version. For questions,
            email <a href="mailto:care@lalaharihealth.com">care@lalaharihealth.com</a>, or use our{" "}
            <Link href="/grievance">Grievance Support page</Link>.
          </p>
        </section>
      </div>
    </Container>
  );
}
