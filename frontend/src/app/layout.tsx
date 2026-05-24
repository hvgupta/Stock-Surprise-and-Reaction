import type { Metadata } from "next";
import { Space_Grotesk, Source_Code_Pro } from "next/font/google";
import "./globals.css";

const displaySans = Space_Grotesk({
  variable: "--font-display-sans",
  subsets: ["latin"],
});

const mono = Source_Code_Pro({
  variable: "--font-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "SP500 Surprise Dashboard",
  description: "Top surprise movers and reaction proportionality insights",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${displaySans.variable} ${mono.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
