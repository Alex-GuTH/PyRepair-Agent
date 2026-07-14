import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PyRepair Agent Public Demo",
  description: "Mock-only WebUI for the PyRepair Agent coding harness.",
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
