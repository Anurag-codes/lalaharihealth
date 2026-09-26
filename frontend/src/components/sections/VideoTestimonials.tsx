import { Star } from "lucide-react";
import { Container } from "@/components/ui/Container";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { VideoPlaceholder } from "@/components/ui/VideoPlaceholder";

// Sample/template stories — replace with real, consented patient testimonials before launch.
const STORIES = [
  {
    name: "Ramesh K.",
    city: "Lucknow, UP",
    quote:
      "I was ready to spend ₹15,000 on tests. The doctor explained it was mild acidity — a home remedy and diet change fixed it in days.",
    saved: "₹14,500",
    videoLabel: "Patient testimonial video: middle-aged man sharing his recovery story at home.",
    imageSrc: "/image_5.png",
  },
  {
    name: "Fatima S.",
    city: "Hyderabad, TS",
    quote:
      "Comparing Ayurvedic and Allopathic options side-by-side finally made sense to me. I chose confidently and felt heard.",
    saved: "₹8,200",
    videoLabel: "Patient testimonial video: young woman speaking to camera in a bright living room.",
    imageSrc: "/image_6.png",
  },
  {
    name: "Arvind P.",
    city: "Pune, MH",
    quote:
      "When I actually needed surgery, they found me a partner hospital that was 30% cheaper than my first quote.",
    saved: "₹1,90,000",
    videoLabel: "Patient testimonial video: senior gentleman with a family member beside him.",
    imageSrc: "/image_7.png",
  },
];

export function VideoTestimonials() {
  return (
    <section id="testimonials" className="scroll-mt-20 bg-primary-soft py-20 sm:py-28">
      <Container>
        <div className="mx-auto max-w-2xl text-center">
          <Eyebrow>Real patients, real savings</Eyebrow>
          <h2 className="mt-5 font-heading text-3xl font-bold tracking-tight text-ink sm:text-4xl">
            Trusted by people just like you
          </h2>
        </div>

        <div className="mt-14 grid grid-cols-1 gap-8 md:grid-cols-3">
          {STORIES.map((story) => (
            <div
              key={story.name}
              className="flex flex-col overflow-hidden rounded-2xl border border-black/5 bg-white shadow-sm"
            >
              <div className="p-3">
                <VideoPlaceholder
                  label={story.videoLabel}
                  imageSrc={story.imageSrc}
                  aspect="aspect-[4/3]"
                />
              </div>
              <div className="flex flex-1 flex-col px-6 pb-6">
                <div className="flex gap-0.5 text-primary">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <Star key={i} className="h-4 w-4" fill="currentColor" />
                  ))}
                </div>
                <p className="mt-3 flex-1 text-sm leading-relaxed text-ink/70">
                  &ldquo;{story.quote}&rdquo;
                </p>
                <div className="mt-5 flex items-center justify-between">
                  <div>
                    <p className="text-sm font-semibold text-ink">{story.name}</p>
                    <p className="text-xs text-ink/50">{story.city}</p>
                  </div>
                  <span className="rounded-full bg-primary-light px-3 py-1 text-xs font-bold text-primary-darker">
                    Saved {story.saved}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </Container>
    </section>
  );
}
