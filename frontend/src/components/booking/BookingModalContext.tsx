"use client";

import { createContext, useContext, useState, type ReactNode } from "react";
import { BookingModal } from "./BookingModal";

type BookingModalContextValue = {
  open: () => void;
  close: () => void;
};

const BookingModalContext = createContext<BookingModalContextValue | null>(null);

export function BookingModalProvider({ children }: { children: ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);
  // Bump on every open so BookingModal remounts fresh (resetting its form state) instead of
  // needing an effect to reset state when reopened.
  const [openKey, setOpenKey] = useState(0);

  return (
    <BookingModalContext.Provider
      value={{
        open: () => {
          setOpenKey((key) => key + 1);
          setIsOpen(true);
        },
        close: () => setIsOpen(false),
      }}
    >
      {children}
      <BookingModal key={openKey} isOpen={isOpen} onClose={() => setIsOpen(false)} />
    </BookingModalContext.Provider>
  );
}

export function useBookingModal() {
  const ctx = useContext(BookingModalContext);
  if (!ctx) {
    throw new Error("useBookingModal must be used within a BookingModalProvider");
  }
  return ctx;
}
