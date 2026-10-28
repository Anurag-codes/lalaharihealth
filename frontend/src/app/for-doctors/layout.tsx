import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Join as a Doctor | LalahariHealth",
  description: "Register as a doctor, hospital or lab with LalahariHealth and reach patients for online consultations.",
  alternates: { canonical: "/for-doctors" },
};

export default function ForDoctorsLayout({ children }: { children: React.ReactNode }) {
  return children;
}
