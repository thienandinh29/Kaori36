import type { Metadata } from "next";
import { Baloo_2, Be_Vietnam_Pro } from "next/font/google";
import { vi } from "@/messages/vi";
import "@xyflow/react/dist/style.css";
import "./globals.css";
import "./english.css";
import "./theme.css";
import "@/components/sena/sena.css";

// Both fonts have full Vietnamese glyphs; next/font self-hosts them at build time (specs/ui-v2).
const display = Baloo_2({
  subsets: ["latin", "vietnamese"],
  weight: ["600", "700", "800"],
  variable: "--font-display",
  display: "swap",
});
const body = Be_Vietnam_Pro({
  subsets: ["latin", "vietnamese"],
  weight: ["400", "500", "600", "700"],
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
