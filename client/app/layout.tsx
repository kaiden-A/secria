import type { Metadata, Viewport } from "next";
import { IBM_Plex_Mono, Manrope, Sora } from "next/font/google";

import { Providers } from "@/components/Providers";

import "./globals.css";

const sora = Sora({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  variable: "--font-sora",
  display: "swap",
});

const manrope = Manrope({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-manrope",
  display: "swap",
});

const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-plex-mono",
  display: "swap",
});

const ICON =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='9' fill='%230A3A46'/%3E%3Ccircle cx='16' cy='12.4' r='4.2' fill='%23C7F464'/%3E%3Cpath d='M13.35 15.9 12 24h8l-1.35-8.1a5.9 5.9 0 0 1-5.3 0Z' fill='%23C7F464'/%3E%3C/svg%3E";

export const metadata: Metadata = {
  title: {
    default: "Secria — self-hosted secrets manager",
    template: "%s · Secria",
  },
  description:
    "Secria is a self-hosted secrets manager with envelope encryption, project-scoped access, audited reveals, and a CLI-native workflow.",
  applicationName: "Secria",
  robots: { index: true, follow: true },
  icons: {
    icon: [{ url: ICON, type: "image/svg+xml" }],
  },
  openGraph: {
    type: "website",
    siteName: "Secria",
    title: "Secria — self-hosted secrets manager",
    description:
      "Ship secrets without shipping them. Envelope-encrypted, versioned, audited, and built for the command line.",
  },
};

export const viewport: Viewport = {
  colorScheme: "light",
  themeColor: "#F7FBFB",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${sora.variable} ${manrope.variable} ${plexMono.variable}`}
    >
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
