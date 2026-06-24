import type { Metadata } from "next";
import Link from "next/link";
import { ClientProviders } from "@/components/ClientProviders";
import { NavClient } from "@/components/NavClient";
import "./globals.css";

export const metadata: Metadata = {
  title: "🧬 CodeDNA",
  description: "AI Code Transparency Tool",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased bg-gray-950 min-h-screen font-sans">
        <ClientProviders>
          {/* Top navigation */}
          <nav className="border-b border-gray-800 bg-gray-950/80 backdrop-blur-sm sticky top-0 z-40">
            <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
              {/* Logo */}
              <Link href="/" className="flex items-center gap-2">
                <span className="text-lg">🧬</span>
                <span className="font-bold text-white">
                  Code<span className="text-cyan-400">DNA</span>
                </span>
              </Link>

              {/* Navigation + language switcher (client component) */}
              <NavClient />
            </div>
          </nav>

          {/* Main content */}
          <main className="max-w-7xl mx-auto px-6 py-8">{children}</main>

          {/* Footer */}
          <footer className="border-t border-gray-800 mt-16">
            <div className="max-w-7xl mx-auto px-6 py-4 text-xs text-gray-700 flex items-center justify-between">
              <span>🧬 CodeDNA</span>
              <a
                href="http://localhost:8000/docs"
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-gray-500 transition-colors"
              >
                FastAPI Docs ↗
              </a>
            </div>
          </footer>
        </ClientProviders>
      </body>
    </html>
  );
}
