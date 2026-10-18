"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { MapPin, X } from "lucide-react";
import { API_BASE_URL } from "@/lib/api";

export type Pricing = {
  country_code: string;
  country_name: string;
  currency: string;
  currency_symbol: string;
  general_fee: number;
  general_fee_display: string;
  general_doctor_payout_display: string;
  doctor_share_percent: number;
  specialist_fee_min: number;
  specialist_fee_max: number;
  specialist_fee_step: number;
  specialist_fee_range_display: string;
  is_fallback: boolean;
};

export const INDIA_PRICING: Pricing = {
  country_code: "IN",
  country_name: "India",
  currency: "INR",
  currency_symbol: "₹",
  general_fee: 200,
  general_fee_display: "₹200",
  general_doctor_payout_display: "₹150",
  doctor_share_percent: 75,
  specialist_fee_min: 200,
  specialist_fee_max: 2000,
  specialist_fee_step: 100,
  specialist_fee_range_display: "₹200–₹2,000",
  is_fallback: true,
};

const STORAGE_KEY = "lalahari-pricing";
const CACHE_MS = 12 * 60 * 60 * 1000;

export function formatAmount(amount: number, symbol: string) {
  const digits = Number.isInteger(amount) ? 0 : 2;
  const value = amount.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
  return /^[A-Za-z]+$/.test(symbol) ? `${symbol} ${value}` : `${symbol}${value}`;
}

const PricingContext = createContext<Pricing>(INDIA_PRICING);

export const usePricing = () => useContext(PricingContext);

function readCache(): Pricing | null {
  try {
    const cached = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
    return cached && Date.now() - cached.savedAt < CACHE_MS ? cached.pricing : null;
  } catch {
    return null;
  }
}

async function fetchPricing(query: string): Promise<Pricing> {
  const response = await fetch(`${API_BASE_URL}/api/v1/pricing/${query}`);
  if (!response.ok) throw new Error("Pricing unavailable");
  return response.json();
}

function currentPosition() {
  return new Promise<GeolocationPosition>((resolve, reject) => {
    if (!navigator.geolocation) return reject(new Error("Geolocation unsupported"));
    navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 20000, maximumAge: CACHE_MS });
  });
}

export function PricingProvider({ children }: { children: ReactNode }) {
  const [pricing, setPricing] = useState<Pricing>(INDIA_PRICING);
  const [asking, setAsking] = useState(false);

  const finish = useCallback((result: Pricing) => {
    setPricing(result);
    setAsking(false);
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ pricing: result, savedAt: Date.now() }));
  }, []);

  useEffect(() => {
    let active = true;
    (async () => {
      await Promise.resolve();
      const cached = readCache();
      if (cached) {
        if (active) setPricing(cached);
        return;
      }
      if (active) setAsking(true);
      let result = INDIA_PRICING;
      try {
        const { coords } = await currentPosition();
        result = await fetchPricing(`?lat=${coords.latitude.toFixed(4)}&lng=${coords.longitude.toFixed(4)}`);
      } catch {
        // Location denied or unavailable: India default (₹200).
        result = await fetchPricing("").catch(() => INDIA_PRICING);
      }
      if (active) finish(result);
    })();
    return () => {
      active = false;
    };
  }, [finish]);

  return (
    <PricingContext.Provider value={pricing}>
      {children}
      {asking && (
        <div
          role="status"
          className="fixed inset-x-3 top-3 z-[70] mx-auto flex max-w-md items-start gap-3 rounded-2xl border border-primary/20 bg-white p-4 text-sm text-ink shadow-xl"
        >
          <MapPin className="mt-0.5 h-5 w-5 shrink-0 text-primary" aria-hidden />
          <p className="flex-1 leading-relaxed">
            Location is required to show you correct doctors of your area. Please allow location access.
          </p>
          <button
            type="button"
            onClick={() => setAsking(false)}
            className="rounded-full p-1 text-ink/50 hover:bg-ink/5 hover:text-ink"
            aria-label="Close location message"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}
    </PricingContext.Provider>
  );
}

export function GeneralFee() {
  return <>{usePricing().general_fee_display}</>;
}

export function GeneralDoctorPayout() {
  return <>{usePricing().general_doctor_payout_display}</>;
}

export function SpecialistFeeMin() {
  const { specialist_fee_min, currency_symbol } = usePricing();
  return <>{formatAmount(specialist_fee_min, currency_symbol)}</>;
}

export function SpecialistFeeMax() {
  const { specialist_fee_max, currency_symbol } = usePricing();
  return <>{formatAmount(specialist_fee_max, currency_symbol)}</>;
}

export function SpecialistFeeRange() {
  return <>{usePricing().specialist_fee_range_display}</>;
}
