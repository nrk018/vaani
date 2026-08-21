import type { Metadata } from "next";
import { Imbue, Victor_Mono } from "next/font/google";
import { TooltipProvider } from "@/components/ui/tooltip";
import "./globals.css";

const victor = Victor_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  weight: ["400", "600", "700"],
});

const imbue = Imbue({
  variable: "--font-serif",
  subsets: ["latin"],
  weight: ["400", "500", "700"],
});

export const metadata: Metadata = {
  title: "Vaani — voice-grounded RAG",
  description:
    "Speak in English or Hindi. Vaani retrieves evidence from MSMARCO-XI and a Goa knowledge pack, then answers only when grounded.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`dark ${victor.variable} ${imbue.variable} h-full antialiased`}
    >
      <body className="grain min-h-full">
        <TooltipProvider>{children}</TooltipProvider>
      </body>
    </html>
  );
}
