"use client";

import { useState } from "react";
import { Phone, Smartphone } from "lucide-react";
import { CallbackForm } from "@/components/booking/CallbackForm";
import { GeneralFee } from "@/components/pricing/PricingContext";

const APP_STORES = ["App Store", "Google Play"];

export function HomeContactActions() {
  const [showCallback, setShowCallback] = useState(false);

  return (
    <div className="mt-6 space-y-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {APP_STORES.map((store) => (
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

      <a
        href="tel:+911800000000"
        className="flex min-h-14 w-full items-center justify-center gap-2 rounded-full bg-primary px-5 py-4 text-base font-bold text-white shadow-lg shadow-primary/25 hover:bg-primary-dark"
      >
        <Phone className="h-5 w-5" />
        Call our executive — <GeneralFee /> consultation
      </a>

      {showCallback ? (
        <CallbackForm autoFocus />
      ) : (
        <button
          type="button"
          onClick={() => setShowCallback(true)}
          className="flex min-h-14 w-full items-center justify-center gap-2 rounded-full border-2 border-primary bg-white px-5 py-3.5 text-base font-bold text-primary-darker hover:bg-primary-light"
        >
          Request a Callback — <GeneralFee /> consultation
        </button>
      )}
    </div>
  );
}
