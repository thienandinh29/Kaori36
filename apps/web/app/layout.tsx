import type { Metadata } from "next";
import localFont from "next/font/local";
import { vi } from "@/messages/vi";
import "@xyflow/react/dist/style.css";
import "./globals.css";
import "./english.css";
import "./theme.css";
import "@/components/sena/sena.css";

// Both fonts are kept in app/fonts (SIL Open Font License, licence files next to them), cut to
// Latin, Latin Extended and Vietnamese, so building never needs the network (specs/ui-v2).
const display = localFont({
  src: "./fonts/Baloo2-Variable.woff2",
  weight: "400 800",
  variable: "--font-display",
  display: "swap",
});
const body = localFont({
  src: [
    { path: "./fonts/BeVietnamPro-400.woff2", weight: "400", style: "normal" },
    { path: "./fonts/BeVietnamPro-500.woff2", weight: "500", style: "normal" },
    { path: "./fonts/BeVietnamPro-600.woff2", weight: "600", style: "normal" },
    { path: "./fonts/BeVietnamPro-700.woff2", weight: "700", style: "normal" },
  ],
  variable: "--font-body",
  display: "swap",
});
export const metadata: Metadata = {
  title: `${vi.app} — ${vi.tagline}`,
  description: vi.intro,
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="vi" className={`${display.variable} ${body.variable}`}>
      <body>{children}</body>
    </html>
  );
}
