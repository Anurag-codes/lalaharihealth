import Image from "next/image";
import { ArrowUpRight } from "lucide-react";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { Button } from "@/components/ui/Button";

const NEWS_SLOTS = [
  {
    id: "medical-debt",
    image: "/healthcare-financial-burden.png",
    imageAlt: "Illustration of a family reviewing medical bills and household expenses at home",
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
    image: "/healthcare-incentives-discussion.png",
    imageAlt: "Illustration of a doctor and patient discussing a medical estimate",
    headline: "The unethical revenue targets that India’s corporate hospitals set their doctors",
    publisher: "The BMJ",
    publishedAt: "3 Sep 2015 · Feature and reader responses",
    summary:
      "The linked page includes reader responses with differing views. BMJ notes that rapid responses are comments, not journal articles; read the original feature and responses in context.",
    href: "https://www.bmj.com/content/351/bmj.h4312/rapid-responses",
  },
  {
    id: "private-healthcare-opinion",
    image: "/private-healthcare-affordability.png",
    imageAlt: "Illustration of a family reviewing medical paperwork outside a hospital",
    headline: "Harsh Mander: The plunder and loot by private healthcare in India",
    publisher: "Scroll.in · Harsh Mander",
    publishedAt: "25 Jun 2025 · Opinion essay",
    summary:
      "An opinion essay discussing affordability, oversight and reported concerns in private healthcare. It presents the author’s argument, not a finding about every hospital or clinician.",
    href: "https://scroll.in/article/1083665/harsh-mander-the-plunder-and-loot-by-private-healthcare-in-india",
  },
];

export function BlogSection({ showReadMore = true }: { showReadMore?: boolean }) {
  return (
    <div id="blogs" className="mt-16 scroll-mt-24 border-t border-black/5 pt-12">
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
          <a
            key={slot.id}
            href={slot.href}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={`Read ${slot.headline} on ${slot.publisher} (opens in a new tab)`}
            className="group flex min-w-0 flex-col overflow-hidden rounded-lg border border-black/10 bg-white transition-shadow hover:shadow-lg focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-primary"
          >
            <div className="relative aspect-video w-full overflow-hidden bg-primary-soft">
              <Image
                src={slot.image}
                alt={slot.imageAlt}
                fill
                sizes="(min-width: 1280px) 390px, (min-width: 768px) 33vw, 100vw"
                className="object-cover transition-transform duration-300 group-hover:scale-[1.03] motion-reduce:transform-none"
              />
            </div>
            <div className="flex flex-1 flex-col p-5">
              <p className="text-xs text-ink/55">AI-generated illustration, not a photograph from the article</p>
              <h4 className="mt-3 font-semibold leading-snug text-ink group-hover:text-primary-darker">
                {slot.headline}
              </h4>
              <p className="mt-2 text-xs font-medium text-ink/50">
                {slot.publisher} · {slot.publishedAt}
              </p>
              <p className="mt-3 flex-1 text-sm leading-relaxed text-ink/65">{slot.summary}</p>
              <span className="mt-4 inline-flex min-h-10 items-center gap-1 text-sm font-semibold text-primary-darker underline underline-offset-2">
                Read original source <ArrowUpRight className="h-4 w-4" />
              </span>
            </div>
          </a>
        ))}
      </div>
      {showReadMore && (
        <div className="mt-10 text-center">
          <Button href="/blogs" variant="outline" size="lg">Read more blogs</Button>
        </div>
      )}
    </div>
  );
}
