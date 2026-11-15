"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";
import { BookingModalProvider } from "@/components/booking/BookingModalContext";
import { PricingProvider } from "@/components/pricing/PricingContext";

export function isStaffPath(pathname: string | null) {
  return pathname === "/staff" || Boolean(pathname?.startsWith("/staff/"));
}

/**
 * Renders the marketing chrome (and the providers it needs) everywhere except the
 * staff console, which has its own minimal shell.
 */
export function SiteChrome({
  announcementBar,
  navbar,
  footer,
  mobileStickyCta,
  floatingCallButton,
  children,
}: {
  announcementBar: ReactNode;
  navbar: ReactNode;
  footer: ReactNode;
  mobileStickyCta: ReactNode;
  floatingCallButton: ReactNode;
  children: ReactNode;
}) {
  const pathname = usePathname();

  if (isStaffPath(pathname)) {
    // The staff console renders its own <main> landmark.
    return <div className="flex flex-1 flex-col">{children}</div>;
  }

  return (
    <PricingProvider>
      <BookingModalProvider>
        {announcementBar}
        {navbar}
        <main className="flex-1 pb-20 lg:pb-0">{children}</main>
        {footer}
        {mobileStickyCta}
        {floatingCallButton}
      </BookingModalProvider>
    </PricingProvider>
  );
}
