"use client";

import { useEffect, useRef, useState } from "react";
import { Phone, Smartphone, X } from "lucide-react";
import { CallbackForm } from "@/components/booking/CallbackForm";
import { useCloseAfterBottomScroll } from "@/hooks/useCloseAfterBottomScroll";
import { GeneralFee } from "@/components/pricing/PricingContext";

export function BookingModal({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const [audioAutoplayBlocked, setAudioAutoplayBlocked] = useState(false);
  const appVideoRef = useRef<HTMLVideoElement>(null);
  const scrollDismissHandlers = useCloseAfterBottomScroll(onClose);

  useEffect(() => {
    if (!isOpen) return;

    document.body.style.overflow = "hidden";
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKey);

    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", handleKey);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="booking-modal-title"
      className="fixed inset-0 z-[100] flex items-start justify-center overflow-y-auto bg-ink/60 p-2 backdrop-blur-sm sm:items-center sm:p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className="my-auto max-h-[calc(100dvh-1rem)] w-full max-w-2xl overflow-y-auto overscroll-contain rounded-2xl bg-white p-4 shadow-2xl sm:max-h-[calc(100dvh-2rem)] sm:rounded-3xl sm:p-8"
        {...scrollDismissHandlers}
      >
        <div className="sticky top-0 z-10 -mx-4 -mt-4 mb-4 flex items-start justify-between gap-4 border-b border-black/5 bg-white px-4 pb-4 pt-3 sm:-mx-8 sm:-mt-8 sm:px-8 sm:pt-5">
          <div>
            <h2
              id="booking-modal-title"
              className="font-heading text-2xl font-bold text-ink sm:text-3xl"
            >
              Choose how you&apos;d like to get help
            </h2>
            <p className="mt-2 text-sm text-ink/70 sm:text-base">
              Registration is free. Consultations are paid; human-assisted consultation is <GeneralFee />.
              Other consultation fees are confirmed before booking.
              Get specialist consultations from home and save time, money, visits to doctors. Our aim is to help you understand the
              care you may need—not push unnecessary tests or treatment for profit.
            </p>
            <p className="font-devanagari mt-2 text-sm leading-relaxed text-primary-darker sm:text-base">
              घर बैठे विशेषज्ञ परामर्श पाएं और समय, पैसा और डॉक्टरों और अस्पतालों के दौरे बचाएं। हमारा उद्देश्य ज़रूरत के अनुसार
              देखभाल समझने में मदद करना है—मुनाफ़े के लिए गैर-ज़रूरी जाँच या इलाज बढ़ावा देना नहीं।
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-ink/60 hover:bg-primary-light hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        <div className="space-y-5" style={{ marginTop: "40px" }}>
          <section aria-labelledby="app-registration-title" className="rounded-2xl border-2 border-primary bg-primary-light p-5 sm:p-6">
            <div className="relative mb-5 overflow-hidden rounded-xl bg-ink">
              <video
                ref={appVideoRef}
                className="aspect-video w-full object-contain"
                src="/videos/generated_video.mp4"
                autoPlay
                controls
                playsInline
                preload="auto"
                aria-label="LalahariHealth app consultation introduction"
                onCanPlay={(event) => {
                  event.currentTarget.play().catch(() => setAudioAutoplayBlocked(true));
                }}
                onPlay={() => setAudioAutoplayBlocked(false)}
              />
              {audioAutoplayBlocked && (
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-ink/75 p-4 text-center">
                  <p className="text-sm font-medium text-white">
                    Tap to start the video with sound.
                  </p>
                  <button
                    type="button"
                    onClick={() => {
                      appVideoRef.current?.play().catch(() => setAudioAutoplayBlocked(true));
                    }}
                    className="min-h-11 rounded-full bg-primary px-5 py-2.5 text-sm font-bold text-white hover:bg-primary-dark"
                  >
                    Play with sound
                  </button>
                </div>
              )}
            </div>
            <div className="flex items-start gap-4">
              <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary text-white">
                <Smartphone className="h-6 w-6" />
              </span>
              <div>
                <h3 id="app-registration-title" className="font-heading text-lg font-bold text-ink sm:text-xl">
                  Register for free on the app
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-ink/70">
                  Registration is free, not the consultation. Consultation fees are confirmed
                  before booking. The app is launching soon.
                </p>
              </div>
            </div>
            <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2">
              {["App Store", "Google Play"].map((store) => (
                <div
                  key={store}
                  aria-disabled="true"
                  title="App launching soon"
                  className="flex cursor-not-allowed items-center justify-between rounded-xl border-2 border-dashed border-primary/30 bg-white px-4 py-3.5 opacity-80"
                >
                  <div className="flex items-center gap-3">
                    <Smartphone className="h-5 w-5 text-primary-darker" />
                    <div>
                      <p className="text-[10px] uppercase tracking-wide text-ink/50">Download on</p>
                      <p className="text-sm font-bold text-ink">{store}</p>
                    </div>
                  </div>
                  <span className="rounded-full bg-primary-light px-2.5 py-1 text-[10px] font-bold uppercase text-primary-darker">
                    Coming soon
                  </span>
                </div>
              ))}
            </div>
          </section>

          <div className="flex items-center gap-4" role="separator" aria-label="Or get help from our team">
            <span className="h-px flex-1 bg-black/10" />
            <span className="text-xs font-semibold uppercase text-ink/45">Or talk to our team</span>
            <span className="h-px flex-1 bg-black/10" />
          </div>

          <section aria-labelledby="executive-title" className="rounded-2xl border border-black/10 bg-white p-5 sm:p-6">
            <div className="flex items-start gap-4">
              <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary-light text-primary-darker">
                <Phone className="h-6 w-6" />
              </span>
              <div>
                <h3 id="executive-title" className="font-heading text-lg font-bold text-ink sm:text-xl">
                  Talk to our executive and get your appointment fixed
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-ink/70">
                  Human-assisted consultation costs <strong className="text-ink"><GeneralFee /></strong>.
                  Our executive will explain the next steps and confirm the appointment and payment.
                </p>
              </div>
            </div>

            <a
              href="tel:+911800000000"
              className="mt-5 flex min-h-14 w-full items-center justify-center gap-2 rounded-full bg-primary px-5 py-4 text-base font-bold text-white shadow-lg shadow-primary/25 hover:bg-primary-dark"
            >
              <Phone className="h-5 w-5" />
              Call our executive — <GeneralFee /> consultation
            </a>

            <div className="my-4 flex items-center gap-3 text-xs font-semibold uppercase tracking-wide text-ink/40">
              <span className="h-px flex-1 bg-ink/10" />
              or request a callback
              <span className="h-px flex-1 bg-ink/10" />
            </div>

            <CallbackForm />
          </section>
        </div>
        <p className="mt-5 text-center text-xs text-ink/45">
          At the end, scroll down twice to close this window.
        </p>
      </div>
    </div>
  );
}
