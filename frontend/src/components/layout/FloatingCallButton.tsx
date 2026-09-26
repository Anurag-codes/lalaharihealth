import { Phone } from "lucide-react";

export function FloatingCallButton() {
  return (
    <a
      href="tel:+911800000000"
      aria-label="Call LalahariHealth now"
      title="Call us: 1800-000-000"
      className="animate-pulse-ring fixed bottom-6 right-6 z-40 hidden h-16 w-16 items-center justify-center rounded-full bg-primary text-white shadow-xl shadow-primary/40 transition-transform hover:scale-105 lg:flex"
    >
      <Phone className="h-7 w-7" />
    </a>
  );
}
