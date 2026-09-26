"use client";

import { useEffect, useState } from "react";
import { Type } from "lucide-react";

const SIZES = ["base", "lg", "xl"] as const;
type TextSize = (typeof SIZES)[number];

const LABELS: Record<TextSize, string> = { base: "A", lg: "A+", xl: "A++" };
const STORAGE_KEY = "lh-text-size";

export function TextSizeControl({ className }: { className?: string }) {
  const [size, setSize] = useState<TextSize>("base");

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY) as TextSize | null;
    if (stored && SIZES.includes(stored)) {
      // Reading a persisted, browser-only preference post-mount avoids an SSR/hydration mismatch.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setSize(stored);
      document.documentElement.dataset.textSize = stored;
    }
  }, []);

  const cycle = () => {
    const next = SIZES[(SIZES.indexOf(size) + 1) % SIZES.length];
    setSize(next);
    document.documentElement.dataset.textSize = next;
    localStorage.setItem(STORAGE_KEY, next);
  };

  return (
    <button
      type="button"
      onClick={cycle}
      aria-label="Adjust text size for easier reading"
      title="Adjust text size"
      className={
        className ??
        "flex h-10 items-center gap-1.5 rounded-full border-2 border-black/10 px-3 text-sm font-bold text-ink/70 hover:border-primary hover:text-primary-darker"
      }
    >
      <Type className="h-4 w-4" />
      {LABELS[size]}
    </button>
  );
}
