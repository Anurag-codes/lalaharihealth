import { Phone } from "lucide-react";
import { BookConsultationButton } from "@/components/ui/BookConsultationButton";

export function MobileStickyCta() {
  return (
    <div className="fixed inset-x-0 bottom-0 z-40 flex items-center gap-3 border-t border-black/5 bg-white/95 p-3 backdrop-blur-md shadow-[0_-4px_20px_rgba(0,0,0,0.06)] lg:hidden">
      <a
        href="tel:+911800000000"
        aria-label="Call us"
        className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full border-2 border-primary text-primary-darker"
      >
        <Phone className="h-5 w-5" />
      </a>
      <BookConsultationButton className="flex-1">
        First App Consultation Free
      </BookConsultationButton>
    </div>
  );
}
