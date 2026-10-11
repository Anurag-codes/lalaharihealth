"use client";

import { motion } from "framer-motion";
import { BadgeCheck, Lock, PlayCircle, Star } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Container } from "@/components/ui/Container";
import { Button } from "@/components/ui/Button";
import { BookConsultationButton } from "@/components/ui/BookConsultationButton";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { FlashingBadge } from "../ui/FlashingBadge";

const POPUP_DISMISSED_EVENT = "lalahari:home-offer-dismissed";

const TRUST_BADGES = [
  { icon: BadgeCheck, label: "Verified Doctors" },
  { icon: Lock, label: "100% Confidential" },
  { icon: Star, label: "4.8/5 Rated" },
];

export function Hero() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const mobileVideoRef = useRef<HTMLVideoElement>(null);
  const [isPopupDismissed, setIsPopupDismissed] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  const startVideo = (video: HTMLVideoElement | null) => {
    if (!video) return;

    video.muted = false;
    video.volume = 1;
    video.currentTime = 0;
    video.play().catch(() => undefined);
  };

  const pauseVideo = (video: HTMLVideoElement | null) => {
    if (!video) return;

    video.pause();
    video.muted = true;
    video.currentTime = 0;
  };

  useEffect(() => {
    const updateViewport = () => setIsMobile(window.innerWidth < 1024);

    updateViewport();
    window.addEventListener("resize", updateViewport);
    return () => window.removeEventListener("resize", updateViewport);
  }, []);

  useEffect(() => {
    const handlePopupDismissed = () => {
      setIsPopupDismissed(true);

      requestAnimationFrame(() => {
        startVideo(videoRef.current);
        startVideo(mobileVideoRef.current);
      });
    };

    window.addEventListener(POPUP_DISMISSED_EVENT, handlePopupDismissed);
    return () => window.removeEventListener(POPUP_DISMISSED_EVENT, handlePopupDismissed);
  }, []);

  useEffect(() => {
    if (!isPopupDismissed) {
      pauseVideo(videoRef.current);
      pauseVideo(mobileVideoRef.current);
      return;
    }

    startVideo(videoRef.current);
    startVideo(mobileVideoRef.current);
  }, [isPopupDismissed]);

  return (
    <section className="relative overflow-hidden pt-14 pb-20 sm:pt-20 sm:pb-28">
      <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(circle_at_85%_10%,rgba(0,167,167,0.12),transparent_45%),radial-gradient(circle_at_5%_85%,rgba(0,167,167,0.10),transparent_40%)]" />

      <Container className="grid grid-cols-1 items-center gap-14 lg:grid-cols-2 lg:gap-10">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <Eyebrow>Trusted by 50,000+ patients across India</Eyebrow>

          <h1 className="mt-6 font-heading text-4xl font-extrabold leading-[1.1] tracking-tight text-ink sm:text-5xl lg:text-[3.4rem]">
            Tests, procedures and hospital bills can add up fast.{" "}
            <span className="text-primary">Ask us before you spend your savings.</span>
          </h1>
          <div className="mt-9 flex flex-wrap items-center gap-x-6 gap-y-3">
            {TRUST_BADGES.map(({ icon: Icon, label }) => (
              <div key={label} className="flex items-center gap-2 text-sm font-medium text-ink/70">
                <Icon className="h-4.5 w-4.5 text-primary" />
                {label}
              </div>
            ))}
          </div>
          <div className="mt-8 flex flex-col gap-4 sm:flex-row">
            {/* <FlashingBadge className="sm:hidden">Limited Time Offer</FlashingBadge> */}
            <div className="relative w-full sm:w-auto">
              <FlashingBadge className="absolute -top-4 left-1/2 hidden -translate-x-1/2 sm:inline-flex">
                Limited Time Offer
              </FlashingBadge>
              <BookConsultationButton className="w-full sm:w-auto">
                Get Your Free Consultation
              </BookConsultationButton>
            </div>
            <Button href="#how-it-works" variant="outline" className="w-full sm:w-auto">
              <PlayCircle className="h-5 w-5" />
              Watch How It Works
            </Button>
          </div>

          <div className="mt-6 max-w-xl space-y-4 text-base leading-relaxed text-ink/70 sm:text-lg">
            <p className="text-primary">
              Get your first symptom-based app consultation free, or consult a specialist from
              home for ₹200. Save travel and waiting time while you understand your next steps.
            </p>
            {isMobile && (
              <div className="mt-2 overflow-hidden rounded-[1.5rem] border border-black/5 bg-white shadow-[0_20px_55px_rgba(15,23,42,0.08)]">
                <video
                  ref={mobileVideoRef}
                  src="/videos/sale_video.mp4"
                  loop
                  playsInline
                  controls
                  muted={!isPopupDismissed}
                  preload="metadata"
                  className="aspect-[4/5] w-full object-cover"
                  aria-label="LalahariHealth doctor consultation overview video"
                />
              </div>
            )}
            <p>
              Before a planned test or procedure, ask why it is recommended, what it may cost, its
              benefits, risks and possible side effects. A second opinion may help you decide.
            </p>
            <p>
              Our aim is to help you understand the care you may need—not push unnecessary tests or
              treatment for profit. Avoiding unnecessary care may help prevent avoidable costs.
              App guidance is not a diagnosis. Do not delay emergency care or skip tests or
              treatment recommended by your clinician.
            </p>
            <p className="text-primary">Telephonic consultation is also available.</p>
            <p className="font-devanagari text-base leading-relaxed text-primary-darker sm:text-lg">
              जाँच, इलाज और अस्पताल के बिल तेज़ी से बढ़ सकते हैं। अपनी बचत खर्च करने से पहले हमसे
              सलाह लें। ऐप पर पहली सलाह मुफ़्त पाएं या घर बैठे ₹200 में विशेषज्ञ से परामर्श लें।
            </p>
            <p className="font-devanagari text-sm leading-relaxed text-ink/65 sm:text-base">
              किसी नियोजित जाँच या प्रक्रिया से पहले उसका कारण, खर्च, लाभ, जोखिम और संभावित दुष्प्रभाव
              पूछें। ज़रूरी इलाज में देरी न करें।
            </p>
          </div>

          

          {/* <div className="mt-9 flex flex-wrap items-center gap-x-6 gap-y-3">
            {TRUST_BADGES.map(({ icon: Icon, label }) => (
              <div key={label} className="flex items-center gap-2 text-sm font-medium text-ink/70">
                <Icon className="h-4.5 w-4.5 text-primary" />
                {label}
              </div>
            ))}
          </div> */}
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.7, delay: 0.15 }}
          className="relative"
        >
          <div className="hidden overflow-hidden rounded-[2rem] border border-black/5 bg-white shadow-[0_32px_90px_rgba(15,23,42,0.10)] lg:block">
            <video
              ref={videoRef}
              src="/videos/sale_video.mp4"
              loop
              playsInline
              controls
              muted={!isPopupDismissed}
              preload="metadata"
              className="aspect-[4/5] w-full object-cover"
              aria-label="LalahariHealth doctor consultation overview video"
            />
          </div>

          <motion.div
            animate={{ y: [0, -10, 0] }}
            transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
            className="absolute -left-4 top-8 hidden rounded-2xl bg-white p-4 shadow-xl sm:block"
          >
            {/* <p className="text-xs font-medium text-ink/50">App registration</p> */}
            <p className="font-heading text-xl font-bold text-primary">App registration</p>
          </motion.div>

          <motion.div
            animate={{ y: [0, 10, 0] }}
            transition={{ duration: 4.5, repeat: Infinity, ease: "easeInOut", delay: 0.5 }}
            className="absolute -right-4 bottom-10 hidden items-center gap-2 rounded-2xl bg-white p-4 shadow-xl sm:flex"
          >
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-primary-light text-primary-darker">
              <BadgeCheck className="h-5 w-5" />
            </span>
            <div>
              <p className="text-xs font-medium text-ink/50">Doctors</p>
              <p className="text-sm font-bold text-ink">100% Verified</p>
            </div>
          </motion.div>
        </motion.div>
      </Container>
    </section>
  );
}
