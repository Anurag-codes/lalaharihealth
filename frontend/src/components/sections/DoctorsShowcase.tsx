import type { ReactNode } from "react";
import { Star } from "lucide-react";
import { Container } from "@/components/ui/Container";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { Button } from "@/components/ui/Button";
import { BookConsultationButton } from "@/components/ui/BookConsultationButton";
import { SiteImage } from "@/components/ui/SiteImage";
import { GeneralFee } from "@/components/pricing/PricingContext";
import { getFeaturedDoctors, type FeaturedDoctor } from "@/lib/doctors";

const DEFAULT_DOCTOR_IMAGE = "/imge_8_9_10.png";

// Same labels doctors pick from on the /for-doctors form.
const SYSTEM_LABELS: Record<string, string> = {
  allopathy: "Allopathic",
  homeopathy: "Homeopathic",
  ayurveda: "Ayurvedic",
  unani: "Unani",
  home_remedy: "Naturopathy",
};

// Sample cards, shown (first two only) until a registered doctor is approved in admin.
const SAMPLE_DOCTORS = [
  {
    name: "Dr. Ananya Sharma",
    specialization: "General Physician",
    systems: ["Allopathy", "Home Remedy"],
    experience: "12 yrs experience",
    rating: "4.9",
    image: DEFAULT_DOCTOR_IMAGE,
  },
  {
    name: "Dr. Surbhi Nair",
    specialization: "Ayurveda Specialist",
    systems: ["Ayurveda", "Home Remedy"],
    experience: "9 yrs experience",
    rating: "4.8",
    image: DEFAULT_DOCTOR_IMAGE,
  },
  {
    name: "Dr. Sana Khan",
    specialization: "Homeopathy Consultant",
    systems: ["Homeopathy"],
    experience: "10 yrs experience",
    rating: "4.9",
    image: DEFAULT_DOCTOR_IMAGE,
  },
  {
    name: "Dr. Imrani Siddiqui",
    specialization: "Unani Physician",
    systems: ["Unani", "Home Remedy"],
    experience: "8 yrs experience",
    rating: "4.7",
    image: DEFAULT_DOCTOR_IMAGE,
  },
];

type DoctorCard = {
  key: string;
  name: string;
  specialization: string;
  systems: string[];
  experience: string;
  rating?: string;
  image: string;
  isUploadedPhoto: boolean;
  fee: ReactNode;
};

function toCard(doctor: FeaturedDoctor): DoctorCard {
  const years = doctor.experience_years;
  return {
    key: `doctor-${doctor.id}`,
    name: doctor.name,
    specialization: doctor.specialization,
    systems: doctor.treatment_systems.map((system) => SYSTEM_LABELS[system] ?? system),
    experience: `${years} ${years === 1 ? "yr" : "yrs"} experience`,
    image: doctor.photo_url ?? DEFAULT_DOCTOR_IMAGE,
    isUploadedPhoto: doctor.photo_url !== null,
    fee: doctor.consultation_category === "specialist" ? doctor.fee_display : <GeneralFee />,
  };
}

// Full class names so Tailwind keeps them; fewer cards stay centred.
const GRID_BY_COUNT: Record<number, string> = {
  1: "mx-auto max-w-xs",
  2: "mx-auto max-w-2xl sm:grid-cols-2",
  3: "mx-auto max-w-5xl sm:grid-cols-2 lg:grid-cols-3",
};

export async function DoctorsShowcase() {
  const registered = await getFeaturedDoctors();
  const doctors: DoctorCard[] = registered.length > 0
    ? registered.map(toCard)
    : SAMPLE_DOCTORS.slice(0, 2).map((doctor) => ({
      ...doctor,
      key: doctor.name,
      isUploadedPhoto: false,
      fee: <GeneralFee />,
    }));
  const gridClass = GRID_BY_COUNT[doctors.length] ?? "sm:grid-cols-2 lg:grid-cols-4";

  return (
    <section id="doctors" className="scroll-mt-20 py-20 sm:py-28">
      <Container>
        <div className="mx-auto max-w-2xl text-center">
          <Eyebrow>Meet the experts</Eyebrow>
          <h2 className="mt-5 font-heading text-3xl font-bold tracking-tight text-ink sm:text-4xl">
            Experienced doctors, across every treatment system
          </h2>
        </div>

        <div className={`mt-14 grid grid-cols-1 gap-6 ${gridClass}`}>
          {doctors.map((doctor) => (
            <div
              key={doctor.key}
              className="overflow-hidden rounded-2xl border border-black/5 bg-white shadow-sm"
            >
              <div className="p-3">
                <SiteImage
                  src={doctor.image}
                  alt={`Portrait of ${doctor.name}`}
                  aspect="aspect-square"
                  rounded="rounded-xl"
                  unoptimized={doctor.isUploadedPhoto}
                />
              </div>
              <div className="px-5 pb-5">
                <div className="flex items-center justify-between">
                  <h3 className="font-heading text-base font-semibold text-ink">
                    {doctor.name}
                  </h3>
                  {doctor.rating && (
                    <span className="flex items-center gap-1 text-xs font-bold text-primary-darker">
                      <Star className="h-3.5 w-3.5" fill="currentColor" />
                      {doctor.rating}
                    </span>
                  )}
                </div>
                <p className="mt-1 text-sm text-ink/60">
                  {doctor.specialization}
                </p>
                <p className="text-xs text-ink/45">{doctor.experience}</p>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {doctor.systems.map((system) => (
                    <span
                      key={system}
                      className="rounded-full bg-primary-light px-2.5 py-1 text-[11px] font-semibold text-primary-darker"
                    >
                      {system}
                    </span>
                  ))}
                </div>
                <div className="mt-4 flex items-center justify-between">
                  <span className="font-heading text-lg font-bold text-ink">
                    {doctor.fee}
                  </span>
                  <BookConsultationButton size="sm">
                    Book
                  </BookConsultationButton>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-12 flex flex-col items-center gap-3 rounded-2xl bg-primary-light px-6 py-8 text-center">
          <h3 className="font-heading text-lg font-semibold text-primary-darker sm:text-xl">
            Are you a doctor or a hospital/clinic/lab?
          </h3>
          <p className="max-w-md text-sm text-primary-darker/80">
            Join LalahariHealth and consult patients online, on your own
            schedule.
          </p>
          <Button href="/for-doctors" variant="secondary">
            Join Now and get Priority Badge on our app
          </Button>
        </div>
      </Container>
    </section>
  );
}
