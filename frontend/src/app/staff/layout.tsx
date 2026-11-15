import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Staff console | LalahariHealth",
  robots: { index: false, follow: false, nocache: true, googleBot: { index: false, follow: false } },
};

export default function StaffRootLayout({ children }: { children: React.ReactNode }) {
  return <div className="min-h-screen flex-1 bg-slate-50 text-ink">{children}</div>;
}
