import type { Metadata } from "next";
import Link from "next/link";
import { Container } from "@/components/ui/Container";
import { Eyebrow } from "@/components/ui/Eyebrow";

export const metadata: Metadata = {
  title: "Privacy Policy | LalahariHealth",
  description: "How LalahariHealth handles personal information and how to contact us about privacy.",
};

export default function PrivacyPage() {
  return (
    <Container className="max-w-3xl py-12 sm:py-20">
      <Eyebrow>Your information matters</Eyebrow>
      <h1 className="mt-5 font-heading text-3xl font-bold text-ink sm:text-4xl">Privacy Policy</h1>
      <p className="mt-3 text-sm text-ink/60">Last updated: 18 October 2026</p>

      <div className="mt-8 space-y-8 text-base leading-relaxed text-ink/75 [&_h2]:mb-3 [&_h2]:font-heading [&_h2]:text-xl [&_h2]:font-semibold [&_h2]:text-ink [&_li]:mt-2 [&_a]:font-medium [&_a]:text-primary-darker [&_a]:underline [&_a]:underline-offset-4">
        <section>
          <h2>1. Who we are and what this policy covers</h2>
          <p>
            LalahariHealth is operated by Algolog Systems Private Limited. This policy describes
            the personal information handled through our website, registration and service
            enquiries, provider applications, and grievance support. Where you use consultation,
            account or payment services, the information associated with those services is also
            covered. App features described as launching soon are not currently available
            through the website.
          </p>
        </section>

        <section>
          <h2>2. Information we collect</h2>
          <ul className="list-disc pl-6">
            <li>
              Contact and enquiry information: your name, phone number, email if supplied, and
              anything you enter in callback requests, complaint forms or messages.
            </li>
            <li>
              Health information you choose to share, such as symptoms, consultation details
              or information about a care-related complaint. Please provide only what is
              needed for your request.
            </li>
            <li>
              Provider applications: doctor or facility details, qualifications, experience,
              specialties, consultation fees, location, and supporting documents you upload.
            </li>
            <li>
              Account, booking and transaction information when you use those services,
              including verified email/phone identities, email verification request records,
              appointment details, payment references and payment status. Email OTPs are
              stored as keyed digests rather than plaintext; rate-limit and token replay
              records support authentication abuse prevention.
            </li>
            <li>
              Approximate location, only if you allow it in your browser or app: your device
              coordinates are sent to our server once to find your country so we can show the
              consultation fee for your area in your currency. We keep only the country and the
              price shown (saved in your browser for up to 12 hours), not your coordinates. If you
              decline, prices are shown in Indian rupees.
            </li>
            <li>
              Browser preferences and technical information: the text-size setting saved in
              your browser, and connection or error information that hosting systems may
              record to operate and troubleshoot the service.
            </li>
          </ul>
          <p className="mt-3">
            Do not send passwords, OTPs, payment PINs, full card numbers or unnecessary identity
            documents through an enquiry or complaint form. If you share someone else&apos;s
            information, ensure you are authorised to do so. A parent or legal guardian should
            handle submissions concerning a child.
          </p>
        </section>

        <section>
          <h2>3. How we use information</h2>
          <p>
            We use information to respond to your enquiries, contact you about a requested
            service, arrange and administer consultations where available, review provider
            applications, process service-related payments, investigate complaints, maintain
            service records, troubleshoot problems and meet applicable legal obligations.
            Submitting a callback request or complaint allows our team to contact you about
            that request. Free registration does not include a free consultation.
          </p>
        </section>

        <section>
          <h2>4. Who may receive information</h2>
          <p>
            Relevant information may be accessed by our team and service providers supporting
            hosting, communications, storage and service administration. When needed for a
            service you request, relevant details may be shared with the practitioner or
            facility involved. Payment services, where used, involve a payment gateway
            (currently Razorpay) and its own handling of payment information. Information may
            also be disclosed where required by applicable law or a valid legal request.
          </p>
          <p className="mt-3">
            Email verification messages are sent through our configured Gmail/Google Workspace
            sender. Phone verification in the mobile app uses Firebase Authentication; the
            backend verifies its token before creating or linking a patient account. These
            Google services process the information needed to deliver and verify the requested
            sign-in. Our backend does not receive your phone SMS OTP.
          </p>
          <p className="mt-3">
            Our complaint form stores your submission in our contact-message system for team
            review; it does not publish your complaint on the website.
          </p>
        </section>

        <section>
          <h2>5. Browser storage, embedded videos and external links</h2>
          <p>
            Our text-size control uses local storage under the key <code>lh-text-size</code> to
            remember your reading preference. You can remove it through your browser&apos;s
            site-data settings. Account or service features may require their own session
            storage or cookies when used.
          </p>
          <p className="mt-3">
            Some pages embed YouTube videos using youtube-nocookie.com. Loading or interacting
            with an embedded video can send connection and device information to YouTube;
            the privacy-enhanced domain does not mean no data is transmitted. External sites
            and payment providers apply their own policies. Blog posts may also embed Vimeo
            videos or load images and MP4 videos from the sources shown in the post.
            Loading that media sends connection information to its provider. See{" "}
            <a href="https://policies.google.com/privacy" target="_blank" rel="noopener noreferrer">
              Google&apos;s privacy policy
            </a>{" "}
            and{" "}
            <a href="https://razorpay.com/privacy/" target="_blank" rel="noopener noreferrer">
              Razorpay&apos;s privacy policy
            </a>, and{" "}
            <a href="https://vimeo.com/privacy" target="_blank" rel="noopener noreferrer">
              Vimeo&apos;s privacy policy
            </a>.
          </p>
        </section>

        <section>
          <h2>6. Retention and security</h2>
          <p>
            Retention depends on the purpose of the record, service requirements, complaint
            handling and applicable legal obligations. There is no single fixed retention
            period stated for every type of information. Contact us to ask about a specific
            record or request deletion. No internet transmission or storage system can be
            guaranteed completely secure; avoid sending sensitive details that are not needed.
          </p>
        </section>

        <section>
          <h2>7. Your choices and privacy requests</h2>
          <p>
            You can ask about the information you provided, request access or correction,
            request deletion, or withdraw permission for optional processing by contacting us.
            We may need to verify your identity before acting on a request. We will assess it
            under applicable law; some information may need to be retained for legal obligations,
            transactions or unresolved disputes. Withdrawing information needed for a requested
            service may mean we cannot continue providing that service.
          </p>
        </section>

        <section>
          <h2>8. Contact and grievances</h2>
          <p>
            For privacy questions or requests, email{" "}
            <a href="mailto:care@lalaharihealth.com">care@lalaharihealth.com</a> with
            &quot;Privacy request&quot; in the subject, or use our{" "}
            <Link href="/grievance">Grievance Support page</Link>. You can also contact our
            founder on <a href="tel:+919818677599">9818677599</a>.
            Include enough information to identify your request, but do not send passwords or OTPs.
          </p>
        </section>

        <section>
          <h2>9. Changes to this policy</h2>
          <p>
            We may update this policy as our services or information-handling practices change.
            The date above identifies the latest version published on this page.
          </p>
        </section>
      </div>
    </Container>
  );
}
