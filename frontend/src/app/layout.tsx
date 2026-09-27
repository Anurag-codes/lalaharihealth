import type { Metadata } from "next";
import { Inter, Noto_Sans_Devanagari, Poppins } from "next/font/google";
import "./globals.css";
import { AnnouncementBar } from "@/components/layout/AnnouncementBar";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { MobileStickyCta } from "@/components/layout/MobileStickyCta";
import { FloatingCallButton } from "@/components/layout/FloatingCallButton";
import { BookingModalProvider } from "@/components/booking/BookingModalContext";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const poppins = Poppins({
  variable: "--font-poppins",
  subsets: ["latin"],
  weight: ["500", "600", "700", "800"],
});

const notoDevanagari = Noto_Sans_Devanagari({
  variable: "--font-noto-devanagari",
  subsets: ["devanagari"],
  weight: ["500", "600", "700"],
});

export const metadata: Metadata = {
  title: "LalahariHealth | Consult Doctors, Compare Treatments, Save Money",
  description:
    // "Get your app-based symptom consultation free. Compare Allopathic, Homeopathic, Ayurvedic, Unani and home-care options, with human-assisted consultation available for ₹200.",
    "Get your app-based symptom consultation free. Compare Allopathic and Natural(home-care) options, with human-assisted consultation available for ₹200.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${poppins.variable} ${notoDevanagari.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col bg-background text-ink">
        <BookingModalProvider>
          <AnnouncementBar />
          <Navbar />
          <main className="flex-1 pb-20 lg:pb-0">{children}</main>
          <Footer />
          <MobileStickyCta />
          <FloatingCallButton />
        </BookingModalProvider>
      </body>
    </html>
  );
}
