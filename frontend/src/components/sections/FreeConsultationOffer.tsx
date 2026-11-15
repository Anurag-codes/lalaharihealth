"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowRight, Gift } from "lucide-react";
import { useBookingModal } from "@/components/booking/BookingModalContext";
import { Container } from "@/components/ui/Container";
import { Button } from "@/components/ui/Button";
import { API_BASE_URL } from "@/lib/api";

type Offer = { coupon_code: string; valid_until: string | null };

export function FreeConsultationOffer() {
  const [offer, setOffer] = useState<Offer | null>(null);
  const { open, closeFreeOffer } = useBookingModal();
  const closeRef = useRef(closeFreeOffer);

  useEffect(() => {
    closeRef.current = closeFreeOffer;
  }, [closeFreeOffer]);

  useEffect(() => {
    const controller = new AbortController();
    let expiryTimer: ReturnType<typeof setTimeout> | undefined;
    let refreshing = false;
    let currentCode: string | null = null;

    function hideOffer() {
      setOffer(null);
      closeRef.current();
      currentCode = null;
    }

    async function refresh() {
      if (refreshing) return;
      refreshing = true;
      try {
        const response = await fetch(`${API_BASE_URL}/api/v1/appointments/free-consultation-offer/`, {
          cache: "no-store", signal: controller.signal,
        });
        if (!response.ok) throw new Error(`Free consultation offer request failed (${response.status}).`);
        const data = await response.json();
        clearTimeout(expiryTimer);
        if (data.available === false && data.offer === null) {
          hideOffer();
          return;
        }
        if (data.available !== true || typeof data.offer?.coupon_code !== "string"
          || data.offer.category !== "general" || data.offer.fee !== 0
          || (data.offer.valid_until !== null && typeof data.offer.valid_until !== "string")) {
          throw new Error("Invalid free consultation offer response.");
        }
        const expiresAt = data.offer.valid_until === null ? null : Date.parse(data.offer.valid_until);
        if (expiresAt !== null && !Number.isFinite(expiresAt)) throw new Error("Invalid free consultation offer expiry.");
        if (expiresAt !== null && expiresAt <= Date.now()) {
          hideOffer();
          return;
        }
        if (currentCode !== null && currentCode !== data.offer.coupon_code) closeRef.current();
        currentCode = data.offer.coupon_code;
        setOffer({ coupon_code: data.offer.coupon_code, valid_until: data.offer.valid_until });
        if (expiresAt !== null && expiresAt - Date.now() <= 2_147_483_647) {
          expiryTimer = setTimeout(hideOffer, expiresAt - Date.now());
        }
      } catch (error) {
        if (controller.signal.aborted) return;
        console.error("Could not load the free consultation offer.", error);
        hideOffer();
      } finally {
        refreshing = false;
      }
    }

    void refresh();
    const interval = setInterval(() => void refresh(), 30_000);
    const onFocus = () => void refresh();
    window.addEventListener("focus", onFocus);
    return () => {
      controller.abort();
      clearInterval(interval);
      clearTimeout(expiryTimer);
      window.removeEventListener("focus", onFocus);
    };
  }, []);

  if (!offer) return null;

  return (
    <section aria-labelledby="free-consultation-title" className="bg-primary-light py-12 sm:py-16">
      <Container>
        <div className="flex flex-col items-start justify-between gap-8 rounded-3xl border-2 border-primary/25 bg-white p-7 shadow-lg shadow-primary/10 sm:p-10 lg:flex-row lg:items-center">
          <div className="max-w-2xl">
            <span className="inline-flex items-center gap-2 rounded-full bg-primary-light px-4 py-2 text-sm font-bold text-primary-darker">
              <Gift className="h-5 w-5" aria-hidden /> Free general consultation
            </span>
            <h2 id="free-consultation-title" className="mt-5 font-heading text-3xl font-extrabold tracking-tight text-ink sm:text-4xl">
              Free consultation by <span className="text-primary-darker">Dr. Banarsi Das</span>
            </h2>
            <p className="mt-4 text-base leading-relaxed text-ink/70">
              Unlimited free bookings while this offer is active. Choose Dr. Banarsi Das for a general
              consultation in the app, or call our team. Staff will confirm your doctor and appointment time.
              Other consultations remain paid.
            </p>
          </div>
          <Button size="lg" className="w-full shrink-0 sm:w-auto" onClick={() => {
            open(offer.coupon_code);
          }}>
            Claim now <ArrowRight className="h-5 w-5" aria-hidden />
          </Button>
        </div>
      </Container>
    </section>
  );
}
