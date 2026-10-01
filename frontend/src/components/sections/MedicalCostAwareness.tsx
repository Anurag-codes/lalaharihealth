import { AlertTriangle, ArrowUpRight, CircleHelp, FileText, PlayCircle } from "lucide-react";
import { Container } from "@/components/ui/Container";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { BookConsultationButton } from "@/components/ui/BookConsultationButton";

const VIDEO_FILE = "patient-treatment-cost-story.mp4";

const NEWS_SLOTS = [
  {
    id: "medical-debt",
    headline:
      "Half the world lacks access to essential health services; health expenses push people into poverty",
    publisher: "World Health Organization and World Bank",
    publishedAt: "13 Dec 2017 · News release",
    summary:
      "A global report on access to essential health services and the financial pressure of out-of-pocket health costs. The figures are global and from 2017.",
    href: "https://www.who.int/news/item/13-12-2017-world-bank-and-who-half-the-world-lacks-access-to-essential-health-services-100-million-still-pushed-into-extreme-poverty-because-of-health-expenses",
  },
  {
    id: "hospital-revenue-debate",
    headline: "The unethical revenue targets that India’s corporate hospitals set their doctors",
    publisher: "The BMJ",
    publishedAt: "3 Sep 2015 · Feature and reader responses",
    summary:
      "The linked page includes reader responses with differing views. BMJ notes that rapid responses are comments, not journal articles; read the original feature and responses in context.",
    href: "https://www.bmj.com/content/351/bmj.h4312/rapid-responses",
  },
  {
    id: "private-healthcare-opinion",
    headline: "Harsh Mander: The plunder and loot by private healthcare in India",
    publisher: "Scroll.in · Harsh Mander",
    publishedAt: "25 Jun 2025 · Opinion essay",
    summary:
      "An opinion essay discussing affordability, oversight and reported concerns in private healthcare. It presents the author’s argument, not a finding about every hospital or clinician.",
    href: "https://scroll.in/article/1083665/harsh-mander-the-plunder-and-loot-by-private-healthcare-in-india",
  },
];

export function MedicalCostAwareness() {
  return (
    <section id="medical-cost-awareness" className="scroll-mt-24 bg-white py-20 sm:py-28">
      <Container>
        <div className="mx-auto max-w-3xl text-center">
          <Eyebrow>Understand before a major decision</Eyebrow>
          <h2 className="mt-5 font-heading text-3xl font-bold tracking-tight text-ink sm:text-4xl">
            Tests, procedures and hospital bills can change a family&apos;s finances
          </h2>
          <p className="mt-4 text-base leading-relaxed text-ink/65 sm:text-lg">
            Medical terms and a long estimate can feel overwhelming. You have the right to ask
            what each planned test or procedure is for, what it may cost, and what benefits, risks
            or alternatives to discuss.
          </p>
        </div>

        <div className="mt-12 grid grid-cols-1 items-start gap-8 lg:grid-cols-2 lg:gap-12">
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
                Start with a free app consultation
              </BookConsultationButton>
            </div>
          </div>
        </div>

        <div className="mt-16 border-t border-black/5 pt-12">
          <div className="mx-auto max-w-2xl text-center">
            <Eyebrow>News and patient stories</Eyebrow>
            <h3 className="mt-4 font-heading text-2xl font-bold text-ink sm:text-3xl">
              Reports, journalism and perspectives on healthcare costs
            </h3>
            <p className="mt-3 text-sm leading-relaxed text-ink/60 sm:text-base">
              These sources discuss healthcare access, medical expenses and concerns about
              incentives in care. They are different kinds of publications—read each in its own
              context; none determines what treatment an individual patient needs.
            </p>
          </div>

          <div className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-3">
            {NEWS_SLOTS.map((slot) => (
              <div key={slot.id} className="rounded-xl border border-dashed border-primary/30 p-5">
                <FileText className="h-5 w-5 text-primary-darker" />
                <h4 className="mt-3 font-semibold leading-snug text-ink">{slot.headline}</h4>
                <p className="mt-2 text-xs font-medium text-ink/50">
                  {slot.publisher} · {slot.publishedAt}
                </p>
                <p className="mt-3 text-sm leading-relaxed text-ink/65">{slot.summary}</p>
                <a
                  href={slot.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-4 inline-flex min-h-10 items-center gap-1 text-sm font-semibold text-primary-darker underline underline-offset-2"
                >
                  Read original source <ArrowUpRight className="h-4 w-4" />
                </a>
              </div>
            ))}
          </div>
        </div>
      </Container>
    </section>
  );
}