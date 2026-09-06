import type { Metadata } from "next";
import { DM_Sans, Instrument_Serif } from "next/font/google";
import "./globals.css";
const dmSans = DM_Sans({ subsets: ["latin"], variable: "--font-sans" });
const instrument = Instrument_Serif({ subsets: ["latin"], variable: "--font-serif", weight: "400" });

export const metadata: Metadata = { title: "APilot", description: "Accounts payable intelligence dashboard" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body className={`${dmSans.variable} ${instrument.variable}`}>{children}</body></html>;
}
