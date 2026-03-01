import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MSME-Graph | AI-Powered MSME Onboarding for ONDC",
  description:
    "Federated AI intelligence system that automates MSME onboarding to the Open Network for Digital Commerce (ONDC). IndiaAI Innovation Challenge 2026.",
  keywords:
    "MSME, ONDC, AI, Graph Neural Network, IndiaAI, OCR, Voice Pipeline, Manufacturing, India",
  openGraph: {
    title: "MSME-Graph | AI-Powered MSME Onboarding for ONDC",
    description:
      "Federated AI intelligence system that automates MSME onboarding to ONDC via the Ministry of MSME's TEAM initiative.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <link
          rel="stylesheet"
          href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
