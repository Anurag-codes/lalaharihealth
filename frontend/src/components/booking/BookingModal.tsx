"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { AlertCircle, CheckCircle2, Loader2, Phone, Smartphone, X } from "lucide-react";
import { API_BASE_URL } from "@/lib/api";
import { useCloseAfterBottomScroll } from "@/hooks/useCloseAfterBottomScroll";

type Status = "idle" | "submitting" | "success" | "error";

export function BookingModal({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const [status, setStatus] = useState<Status>("idle");
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

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setStatus("submitting");
    const formData = new FormData(event.currentTarget);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/core/contact-messages/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: formData.get("name"),
          phone_number: formData.get("phone_number"),
          message:
            "Callback requested for a human-assisted consultation (₹200). Executive to explain the fee and confirm the appointment.",
        }),
      });
      if (!response.ok) throw new Error("Request failed");
      setStatus("success");
    } catch {
      setStatus("error");
    }
  };

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
              Start with free app consultation, or ask our team to arrange a personal consultation.
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
          <section aria-labelledby="free-app-title" className="rounded-2xl border-2 border-primary bg-primary-light p-5 sm:p-6">
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
                <h3 id="free-app-title" className="font-heading text-lg font-bold text-ink sm:text-xl">
                  Get your free consultation on the app
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-ink/70">
                  Describe your symptoms in the app and receive your app-generated consultation
                  free. The app is launching soon.
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
                  Human-assisted consultation costs <strong className="text-ink">₹200</strong>.
                  Our executive will explain the next steps and confirm the appointment and payment.
                </p>
              </div>
            </div>

            <a
              href="tel:+911800000000"
              className="mt-5 flex min-h-14 w-full items-center justify-center gap-2 rounded-full bg-primary px-5 py-4 text-base font-bold text-white shadow-lg shadow-primary/25 hover:bg-primary-dark"
            >
              <Phone className="h-5 w-5" />
              Call our executive — ₹200 consultation
            </a>

            <div className="my-4 flex items-center gap-3 text-xs font-semibold uppercase tracking-wide text-ink/40">
              <span className="h-px flex-1 bg-ink/10" />
              or request a callback
              <span className="h-px flex-1 bg-ink/10" />
            </div>

            {status === "success" ? (
              <div className="flex flex-col items-center gap-2 rounded-2xl bg-primary-light px-4 py-6 text-center">
                <CheckCircle2 className="h-9 w-9 text-primary-darker" />
                <p className="text-sm font-semibold text-ink">
                  Callback requested. Our executive will explain the ₹200 consultation and confirm
                  your appointment.
                </p>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <input
                  name="name"
                  type="text"
                  required
                  placeholder="Your name"
                  aria-label="Your name"
                  className="w-full rounded-xl border border-black/10 bg-white px-4 py-3.5 text-base text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                />
                <input
                  name="phone_number"
                  type="tel"
                  required
                  placeholder="Your phone number"
                  aria-label="Your phone number"
                  className="w-full rounded-xl border border-black/10 bg-white px-4 py-3.5 text-base text-ink outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                />
                {status === "error" && (
                  <div className="flex items-center gap-2 rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700 sm:col-span-2">
                    <AlertCircle className="h-4 w-4 shrink-0" />
                    Something went wrong. Please call our executive instead.
                  </div>
                )}
                <button
                  type="submit"
                  disabled={status === "submitting"}
                  className="flex min-h-14 w-full items-center justify-center gap-2 rounded-full border-2 border-primary bg-white px-5 py-3.5 text-base font-bold text-primary-darker hover:bg-primary-light disabled:cursor-not-allowed disabled:opacity-70 sm:col-span-2"
                >
                  {status === "submitting" ? (
                    <>
                      <Loader2 className="h-5 w-5 animate-spin" /> Sending...
                    </>
                  ) : (
                    "Request a Callback — ₹200 consultation"
                  )}
                </button>
              </form>
            )}
          </section>
        </div>
        <p className="mt-5 text-center text-xs text-ink/45">
          At the end, scroll down twice to close this window.
        </p>
      </div>
    </div>
  );
}
