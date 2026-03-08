import type { Metadata, Viewport } from "next";
import "./globals.css";
import { AppShell } from "@/components/AppShell";

export const metadata: Metadata = {
  title: "NEXUS-NODE | Autonomous Action Mesh",
  description:
    "NEXUS-NODE — an autonomous, low-latency enterprise Action Mesh powered by LangGraph, Groq, and Gemini Flash with full 2026 governance.",
  keywords: [
    "LangGraph",
    "AI agent",
    "enterprise",
    "action mesh",
    "Groq",
    "Gemini",
  ],
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin=""
        />
        {/* Suppress MetaMask & browser-extension runtime errors */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              window.addEventListener('error', function(e) {
                if (
                  e.message && (
                    e.message.includes('MetaMask') ||
                    e.message.includes('ethereum') ||
                    e.message.includes('chrome-extension') ||
                    e.message.includes('Failed to connect')
                  )
                ) { e.stopImmediatePropagation(); e.preventDefault(); return false; }
              }, true);
              window.addEventListener('unhandledrejection', function(e) {
                if (
                  e.reason && e.reason.message && (
                    e.reason.message.includes('MetaMask') ||
                    e.reason.message.includes('ethereum') ||
                    e.reason.message.includes('chrome-extension')
                  )
                ) { e.preventDefault(); }
              });
            `,
          }}
        />
      </head>
      <body
        className="bg-nexus-bg text-nexus-text antialiased"
        suppressHydrationWarning
      >
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
