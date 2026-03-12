import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Calyx Containers — Instant Quote",
  description:
    "Get instant pricing for custom cannabis packaging. Compare Digital, Flexographic, and International production methods side by side.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
