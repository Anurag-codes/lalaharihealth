"use client";

import { Play } from "lucide-react";
import { clsx } from "clsx";
import Image from "next/image";

type VideoPlaceholderProps = {
  label?: string;
  imageSrc?: string;
  duration?: string;
  aspect?: string;
  className?: string;
};

/**
 * Styled stand-in for a real trust-building video (testimonial, demo, etc).
 * Swap the inner content for a real <video>/YouTube embed once footage is ready.
 */
export function VideoPlaceholder({
  label,
  imageSrc,
  duration,
  aspect = "aspect-video",
  className,
}: VideoPlaceholderProps) {
  return (
    <div
      className={clsx(
        aspect,
        "group relative flex w-full cursor-pointer flex-col items-center justify-center gap-3 overflow-hidden rounded-3xl border-2 border-dashed border-primary/30 bg-gradient-to-br from-primary-darker via-primary-dark to-primary p-6 text-center",
        className,
      )}
    >
      {imageSrc && (
        <Image
          src={imageSrc}
          alt=""
          fill
          sizes="(min-width: 768px) 33vw, 100vw"
          className="object-cover"
        />
      )}
      <div className="absolute inset-0 bg-black/30" />
      {!imageSrc && (
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(255,255,255,0.15),transparent_60%)]" />
      )}
      <span className="relative flex h-16 w-16 items-center justify-center rounded-full bg-white/90 shadow-lg transition-transform group-hover:scale-110">
        <Play className="ml-1 h-7 w-7 text-primary-darker" fill="currentColor" />
      </span>
      <p className="relative max-w-xs text-xs font-medium leading-relaxed text-white/90 sm:text-sm">
        {label}
      </p>
      {duration && (
        <span className="relative rounded-full bg-black/30 px-3 py-1 text-[11px] font-semibold text-white">
          {duration}
        </span>
      )}
    </div>
  );
}
