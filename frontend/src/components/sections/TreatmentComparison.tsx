import { Droplet, FlaskConical, Home as HomeIcon, Leaf, Pill } from "lucide-react";
import { Container } from "@/components/ui/Container";
import { Eyebrow } from "@/components/ui/Eyebrow";

const SYSTEMS = [
  {
    icon: Pill,
    name: "Allopathic",
    text: "Fast, evidence-based relief for acute or serious conditions. Best when you need quick results.",
    cost: "₹500 – ₹5,000+",
  },
  {
    icon: Droplet,
    name: "Homeopathic",
    text: "Gentle, low-dose treatment for chronic issues, allergies and lifestyle conditions.",
    cost: "₹300 – ₹1,500",
  },
  {
    icon: Leaf,
    name: "Ayurvedic",
    text: "Holistic healing with diet & lifestyle correction to fix the root cause, not just symptoms.",
    cost: "₹400 – ₹2,000",
  },
  {
    icon: FlaskConical,
    name: "Unani",
    text: "Natural herbal formulations for mild-to-moderate conditions, gentle on the body.",
    cost: "₹300 – ₹1,800",
  },
  {
    icon: HomeIcon,
    name: "Home Remedy",
    text: "Doctor-approved kitchen-ingredient remedies for everyday, minor issues.",
    cost: "₹0 – ₹200",
    highlight: true,
  },
];

const EXAMPLE_BARS = [
  { name: "Allopathic", cost: "₹2,500", width: "100%" },
  { name: "Homeopathic", cost: "₹900", width: "36%" },
  { name: "Ayurvedic", cost: "₹1,100", width: "44%" },
  { name: "Unani", cost: "₹850", width: "34%" },
  { name: "Home Remedy", cost: "₹150", width: "8%", highlight: true },
];

export function TreatmentComparison() {
  return (
    <section id="compare-treatments" className="scroll-mt-20 py-20 sm:py-28">
      <Container>
        <div className="mx-auto max-w-2xl text-center">
          <Eyebrow>Compare before you spend</Eyebrow>
          <h2 className="mt-5 font-heading text-3xl font-bold tracking-tight text-ink sm:text-4xl">
            One symptom. Five treatment paths. You decide.
          </h2>
          <p className="mt-4 text-base leading-relaxed text-ink/60 sm:text-lg">
            Our doctors lay out every credible option honestly — including the ones that cost
            almost nothing — so you never overpay out of fear or confusion.
          </p>
        </div>

        <div className="mt-14 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-5">
          {SYSTEMS.map(({ icon: Icon, name, text, cost, highlight }) => (
            <div
              key={name}
              className={
                highlight
                  ? "rounded-2xl border-2 border-primary bg-primary-light p-6 shadow-md shadow-primary/10"
                  : "rounded-2xl border border-black/5 bg-white p-6 shadow-sm shadow-black/[0.02]"
              }
            >
              <span
                className={
                  highlight
                    ? "flex h-12 w-12 items-center justify-center rounded-xl bg-primary text-white"
                    : "flex h-12 w-12 items-center justify-center rounded-xl bg-primary-light text-primary-darker"
                }
              >
                <Icon className="h-6 w-6" />
              </span>
              <h3 className="mt-5 font-heading text-lg font-semibold text-ink">{name}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink/60">{text}</p>
              <p className="mt-4 inline-flex rounded-full bg-white px-3 py-1 text-xs font-bold text-primary-darker shadow-sm">
                {cost}
              </p>
            </div>
          ))}
        </div>

        <div className="mt-16 rounded-3xl border border-black/5 bg-white p-6 shadow-sm sm:p-10">
          <h3 className="font-heading text-xl font-bold text-ink sm:text-2xl">
            Example: Seasonal Cold &amp; Body Ache
          </h3>
          <p className="mt-2 text-sm text-ink/60">
            Illustrative cost comparison a doctor might walk you through on your call.
          </p>

          <div className="mt-8 space-y-5">
            {EXAMPLE_BARS.map((bar) => (
              <div key={bar.name}>
                <div className="mb-1.5 flex items-center justify-between text-sm font-semibold text-ink">
                  <span>{bar.name}</span>
                  <span className={bar.highlight ? "text-primary-darker" : "text-ink/70"}>
                    {bar.cost}
                  </span>
                </div>
                <div className="h-3 w-full overflow-hidden rounded-full bg-primary-soft">
                  <div
                    style={{ width: bar.width }}
                    className={
                      bar.highlight
                        ? "h-full rounded-full bg-gradient-to-r from-primary-dark to-primary"
                        : "h-full rounded-full bg-ink/25"
                    }
                  />
                </div>
              </div>
            ))}
          </div>
          <p className="mt-6 text-xs text-ink/45">
            Cost estimates are illustrative averages for guidance only and vary by city, severity
            and individual case — always follow your doctor&apos;s specific advice.
          </p>
        </div>
      </Container>
    </section>
  );
}
