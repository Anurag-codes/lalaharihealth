import { clsx } from "clsx";

// A small, flashing red pill used to nudge urgency next to primary CTAs.
export function FlashingBadge({
  children = "Limited Time Offer",
  className,
}: {
  children?: React.ReactNode;
  className?: string;
}) {
  return (
    <span
      role="status"
      style={{ width: "max-content" }}
      className={clsx(
        "animate-flash-urgent inline-flex items-center gap-1.5 rounded-full bg-red-600 px-3 py-1 text-[11px] font-bold uppercase tracking-wide text-white shadow-md shadow-red-600/30",
        className,
      )}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-white" />
      {children}
    </span>
  );
}
