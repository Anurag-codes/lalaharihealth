import { Container } from "@/components/ui/Container";

const STATS = [
  { value: "10+", label: "Verified Doctors" },
  { value: "1,000+", label: "Consultations Done" },
  { value: "5", label: "Treatment Systems Compared" },
  { value: "₹1L+", label: "Saved for Patients" },
];

export function TrustStats() {
  return (
    <section className="bg-gradient-to-r from-primary-darker via-primary-dark to-primary">
      <Container className="grid grid-cols-2 gap-8 py-10 sm:py-12 lg:grid-cols-4">
        {STATS.map((stat) => (
          <div key={stat.label} className="text-center">
            <p className="font-heading text-3xl font-extrabold text-white sm:text-4xl">
              {stat.value}
            </p>
            <p className="mt-1 text-xs font-medium text-white/75 sm:text-sm">{stat.label}</p>
          </div>
        ))}
      </Container>
    </section>
  );
}
