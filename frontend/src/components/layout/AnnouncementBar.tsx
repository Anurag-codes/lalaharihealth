"use client";

import { useState } from "react";
import { Rocket, X } from "lucide-react";

export function AnnouncementBar() {
  const [visible, setVisible] = useState(true);

  if (!visible) return null;

  return (
    <div className="relative flex items-center justify-center gap-3 bg-ink px-4 py-2.5 text-center text-white">
      <Rocket className="h-4 w-4 shrink-0 text-primary" />
      <p className="text-xs font-medium sm:text-sm">
        App launching soon: get your app consultation free. Human-assisted consultation: ₹100.
      </p>
      <button
        type="button"
        onClick={() => setVisible(false)}
        aria-label="Dismiss announcement"
        className="absolute right-3 flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-white/70 hover:bg-white/10 hover:text-white"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}
