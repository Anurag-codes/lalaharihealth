"use client";

import { getButtonClasses, type Size, type Variant } from "@/components/ui/Button";
import { useBookingModal } from "@/components/booking/BookingModalContext";

export function BookConsultationButton({
  variant = "primary",
  size = "md",
  className,
  children = "Book Consultation",
  onBeforeOpen,
}: {
  variant?: Variant;
  size?: Size;
  className?: string;
  children?: React.ReactNode;
  onBeforeOpen?: () => void;
}) {
  const { open } = useBookingModal();

  return (
    <button
      type="button"
      onClick={() => {
        onBeforeOpen?.();
        open();
      }}
      className={getButtonClasses(variant, size, className)}
    >
      {children}
    </button>
  );
}
