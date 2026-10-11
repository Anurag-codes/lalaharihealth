import { ArrowUpRight, Smartphone } from "lucide-react";
import { Container } from "@/components/ui/Container";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { BookConsultationButton } from "@/components/ui/BookConsultationButton";

const VIDEOS = [
  {
    id: "jJO4-9VS2A0",
    title: "Hospital bills and the impact on families",
    description: "A third-party video shared for discussion about healthcare costs and patient experiences.",
  },
];

export function HealthcareVideoStories() {
  return (
    <section aria-labelledby="healthcare-stories-title" className="border-b border-black/5 bg-primary-soft py-10 sm:py-14">
      <Container>
        <div className="grid items-center gap-8 lg:grid-cols-[1.2fr_1fr] lg:gap-14">
          <div>
            <Eyebrow>The concern behind LalahariHealth</Eyebrow>
            <h2 id="healthcare-stories-title" className="mt-5 font-heading text-3xl font-bold leading-tight text-ink sm:text-4xl">
              A hospital bill can affect the whole family.
            </h2>
            <p className="mt-4 max-w-xl text-base leading-relaxed text-ink/75 sm:text-lg">
              Tests, treatment costs and repeated visits can put pressure on your savings.
              LalahariHealth was started to make initial guidance more accessible and help people
              ask informed questions before planned care.
            </p>
            <p lang="hi" className="mt-4 max-w-xl font-devanagari text-base leading-relaxed text-primary-darker sm:text-lg">
              अस्पताल का बड़ा बिल पूरे परिवार पर असर डाल सकता है। घर बैठे शुरुआती सलाह लें और
              नियोजित जाँच या इलाज से पहले अपने सवाल पूछें।
            </p>
            <div className="mt-6">
              <BookConsultationButton size="lg" className="w-full sm:w-auto">
                <Smartphone className="h-5 w-5 shrink-0" />
                Get free app guidance / consultation options
              </BookConsultationButton>
            </div>
            <p className="mt-3 max-w-xl text-sm leading-relaxed text-ink/65">
              App download availability is shown in the booking window. App guidance is not a
              diagnosis; never delay emergency care or stop prescribed treatment.
            </p>
          </div>

          <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,16rem),1fr))] justify-items-center gap-6">
            {VIDEOS.map((video) => (
              <article key={video.id} className="w-full max-w-[20rem] min-w-0">
                <div className="aspect-[9/16] w-full overflow-hidden rounded-lg bg-black">
                  <iframe
                    src={`https://www.youtube-nocookie.com/embed/${video.id}?playsinline=1&rel=0`}
                    title={`YouTube video: ${video.title}`}
                    className="h-full w-full border-0"
                    loading="lazy"
                    allow="accelerometer; encrypted-media; gyroscope; picture-in-picture; fullscreen"
                    referrerPolicy="strict-origin-when-cross-origin"
                    allowFullScreen
                  />
                </div>
                <h3 className="mt-3 font-heading text-base font-semibold text-ink">{video.title}</h3>
                <p className="mt-1 text-sm leading-relaxed text-ink/65">{video.description}</p>
                <a
                  href={`https://www.youtube.com/shorts/${video.id}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-2 inline-flex min-h-11 items-center gap-2 text-sm font-semibold text-primary-darker underline underline-offset-4"
                >
                  Watch on YouTube <ArrowUpRight className="h-4 w-4" />
                </a>
              </article>
            ))}
          </div>
        </div>
        <p className="mt-6 border-t border-black/10 pt-4 text-sm leading-relaxed text-ink/60">
          These videos express their creators&apos; perspectives, not findings about every hospital
          or doctor. They do not establish whether a particular patient needs a test or procedure,
          and their inclusion does not imply the creators endorse LalahariHealth.
        </p>
      </Container>
    </section>
  );
}