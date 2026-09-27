"use client";

import { motion } from "framer-motion";
import { BadgeCheck, Lock, PlayCircle, Star } from "lucide-react";
import { Container } from "@/components/ui/Container";
import { Button } from "@/components/ui/Button";
import { BookConsultationButton } from "@/components/ui/BookConsultationButton";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { SiteImage } from "@/components/ui/SiteImage";

const TRUST_BADGES = [
  { icon: BadgeCheck, label: "Verified Doctors" },
  { icon: Lock, label: "100% Confidential" },
  { icon: Star, label: "4.8/5 Rated" },
];

export function Hero() {
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
            Don&apos;t sell your property or take heavy loans for treatment.{" "}
            <span className="text-primary">Free home consultations and cheapest treatment to all.</span>
          </h1>

          <div className="mt-6 max-w-xl space-y-4 text-base leading-relaxed text-ink/70 sm:text-lg">
            <p className="text-primary">
              Get cheapest specialist consultations from home and save travel time, wait time, money, visits to doctors and hospitals and avoid unnecessary tests and treatments.
            </p>
            <p>
              Tell the LalahariHealth app what&apos;s troubling you and get your first
              symptom-based guidance free. Understand your next steps before making costly
              decisions.
            </p>
            <p>
              Our aim is to help you understand the care you may need—not push unnecessary tests or
              treatment for profit. Avoiding unnecessary care may help prevent avoidable costs.
            </p>
            <p className="text-primary">Telephonic consultation is also available.</p>
            <p className="font-devanagari text-base leading-relaxed text-primary-darker sm:text-lg">
              घर बैठे विशेषज्ञ परामर्श पाएं और समय, पैसा और डॉक्टरों और अस्पतालों के दौरे बचाएं।  
              सेहत की परेशानी या इलाज के खर्च की चिंता? ऐप पर अपनी तकलीफ़ बताइए और पहली सलाह
              मुफ़्त पाइए।
            </p>
            <p className="font-devanagari text-base leading-relaxed text-primary-darker sm:text-lg">
              हमारा उद्देश्य ज़रूरत के अनुसार
              देखभाल समझने में मदद करना है—मुनाफ़े के लिए गैर-ज़रूरी जाँच या इलाज बढ़ावा देना नहीं।
              इससे बेवजह के खर्च से बचने में मदद मिल सकती है।
              <span className="text-primary">टेलीफोनिक परामर्श भी उपलब्ध है।</span>
            </p>
          </div>

          <div className="mt-8 flex flex-col gap-4 sm:flex-row">
            <BookConsultationButton size="lg">Get Your First Consultation Free</BookConsultationButton>
            <Button href="#how-it-works" variant="outline" size="lg">
              <PlayCircle className="h-5 w-5" />
              Watch How It Works
            </Button>
          </div>

          <div className="mt-9 flex flex-wrap items-center gap-x-6 gap-y-3">
            {TRUST_BADGES.map(({ icon: Icon, label }) => (
              <div key={label} className="flex items-center gap-2 text-sm font-medium text-ink/70">
                <Icon className="h-4.5 w-4.5 text-primary" />
                {label}
              </div>
            ))}
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.7, delay: 0.15 }}
          className="relative"
        >
          <SiteImage
            src="/image_1.png"
            alt="Doctor consulting a patient over a video call"
            aspect="aspect-[4/5]"
            priority
          />

          <motion.div
            animate={{ y: [0, -10, 0] }}
            transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
            className="absolute -left-4 top-8 hidden rounded-2xl bg-white p-4 shadow-xl sm:block"
          >
            <p className="text-xs font-medium text-ink/50">First app consultation</p>
            <p className="font-heading text-xl font-bold text-primary">Free</p>
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
