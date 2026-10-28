import { API_BASE_URL } from "@/lib/api";

export type FeaturedDoctor = {
  id: number;
  name: string;
  qualification: string;
  specialization: string;
  experience_years: number | null;
  consultation_category: "general" | "specialist" | "";
  treatment_systems: string[];
  consultation_fee: number | null;
  currency: string;
  fee_display: string | null;
  photo_url: string | null;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isPhotoUrl(value: unknown): value is string | null {
  if (value === null) return true;
  if (typeof value !== "string") return false;
  try {
    return ["http:", "https:"].includes(new URL(value).protocol);
  } catch {
    return false;
  }
}

function isFeaturedDoctor(value: unknown): value is FeaturedDoctor {
  return isRecord(value) && Number.isSafeInteger(value.id) &&
    typeof value.name === "string" && typeof value.qualification === "string" &&
    typeof value.specialization === "string" && (value.experience_years === null || Number.isSafeInteger(value.experience_years)) &&
    (value.consultation_category === "general" || value.consultation_category === "specialist" || value.consultation_category === "") &&
    Array.isArray(value.treatment_systems) && value.treatment_systems.every((item) => typeof item === "string") &&
    (value.consultation_fee === null || typeof value.consultation_fee === "number") && typeof value.currency === "string" &&
    (value.fee_display === null || typeof value.fee_display === "string") && isPhotoUrl(value.photo_url);
}

// Approved doctors registered through /for-doctors. Returns [] when the API is
// unreachable so the homepage can fall back to the sample cards.
export async function getFeaturedDoctors(): Promise<FeaturedDoctor[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/doctors/featured/`, {
      next: { revalidate: 60 },
      signal: AbortSignal.timeout(5000),
    });
    if (!response.ok) return [];
    const data: unknown = await response.json();
    return Array.isArray(data) ? data.filter(isFeaturedDoctor) : [];
  } catch {
    return [];
  }
}
