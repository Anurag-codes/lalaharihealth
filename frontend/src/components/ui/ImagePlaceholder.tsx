import { ImageIcon } from "lucide-react";
import { clsx } from "clsx";

type ImagePlaceholderProps = {
  label: string;
  aspect?: string;
  className?: string;
  rounded?: string;
  tone?: "light" | "dark";
};

/**
 * Styled stand-in for a real photo/illustration. Replace with a Next.js
 * <Image> once real assets are sourced. `label` should describe exactly
 * what to shoot/download so it's easy to swap in real content later.
 */
export function ImagePlaceholder({
  label,
  aspect = "aspect-[4/3]",
  className,
  rounded = "rounded-3xl",
  tone = "light",
}: ImagePlaceholderProps) {
  return (
    <div
      className={clsx(
        aspect,
        rounded,
        "flex w-full flex-col items-center justify-center gap-3 border-2 border-dashed p-6 text-center",
        tone === "light"
          ? "border-primary/30 bg-gradient-to-br from-primary-light via-primary-soft to-white"
          : "border-white/40 bg-gradient-to-br from-white/10 via-white/5 to-transparent",
        className,
      )}
    >
      <ImageIcon
        className={clsx("h-8 w-8 shrink-0", tone === "light" ? "text-primary/60" : "text-white/70")}
        strokeWidth={1.5}
      />
      <p
        className={clsx(
          "text-xs font-medium leading-relaxed sm:text-sm",
          tone === "light" ? "text-primary-darker/70" : "text-white/80",
        )}
      >
        {label}
      </p>
    </div>
  );
}
