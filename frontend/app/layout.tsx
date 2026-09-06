import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  applicationName: "APilot",
  title: "APilot — Control Desk",
  description:
    "Accounts-payable exception control: APilot matches invoices to PO and goods-receipt evidence, posts clean invoices automatically, and frames every exception with the control that failed.",
  icons: {
    icon: "/icon.svg",
    shortcut: "/icon.svg",
    apple: "/icon.svg",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
