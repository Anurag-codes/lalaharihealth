export const IST_OFFSET = "+05:30";
export const IST_TIME_ZONE = "Asia/Kolkata";
export const SLOT_MINUTES = 15;
export const BOOKING_WINDOW_DAYS = 30;

/** Every 15-minute slot start of a day, as minutes after midnight (0 … 1425). */
export const DAY_SLOTS: number[] = Array.from({ length: (24 * 60) / SLOT_MINUTES }, (_, i) => i * SLOT_MINUTES);

const partsFormatter = new Intl.DateTimeFormat("en-CA", {
  timeZone: IST_TIME_ZONE,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

function indiaParts(date: Date) {
  const parts = Object.fromEntries(partsFormatter.formatToParts(date).map((p) => [p.type, p.value]));
  const hour = Number(parts.hour) % 24;
  return {
    date: `${parts.year}-${parts.month}-${parts.day}`,
    minutes: hour * 60 + Number(parts.minute),
  };
}

/** Current India date (YYYY-MM-DD) and minutes after midnight, regardless of browser time zone. */
export function getIndiaNow() {
  return indiaParts(new Date());
}

/** India-local date + minutes for an ISO timestamp. */
export function toIndiaDateMinutes(iso: string | null | undefined) {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return indiaParts(d);
}

export function isValidDateString(value: string | null | undefined): value is string {
  return Boolean(value && /^\d{4}-\d{2}-\d{2}$/.test(value) && !Number.isNaN(Date.parse(`${value}T00:00:00Z`)));
}

export function addDays(date: string, days: number) {
  const d = new Date(`${date}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

export function pad2(n: number) {
  return String(n).padStart(2, "0");
}

export function buildStartsAt(date: string, minutes: number) {
  return `${date}T${pad2(Math.floor(minutes / 60))}:${pad2(minutes % 60)}:00${IST_OFFSET}`;
}

export function formatSlotLabel(minutes: number) {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  const suffix = h < 12 ? "AM" : "PM";
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return `${h12}:${pad2(m)} ${suffix}`;
}

export function isSlotPast(date: string, minutes: number, now: { date: string; minutes: number }) {
  return date < now.date || (date === now.date && minutes <= now.minutes);
}

const dateTimeFormatter = new Intl.DateTimeFormat("en-IN", {
  timeZone: IST_TIME_ZONE,
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "numeric",
  minute: "2-digit",
  hour12: true,
});

const dateFormatter = new Intl.DateTimeFormat("en-IN", {
  timeZone: IST_TIME_ZONE,
  weekday: "short",
  day: "numeric",
  month: "short",
  year: "numeric",
});

export function formatDateTime(iso: string | null | undefined) {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : dateTimeFormatter.format(d);
}

/** Formats a YYYY-MM-DD calendar date (interpreted as an India date). */
export function formatDate(date: string | null | undefined) {
  if (!isValidDateString(date)) return date || "—";
  return dateFormatter.format(new Date(`${date}T12:00:00${IST_OFFSET}`));
}

export function formatDuration(seconds: number | null | undefined) {
  if (seconds === null || seconds === undefined) return "—";
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m ? `${m}m ${pad2(s)}s` : `${s}s`;
}
