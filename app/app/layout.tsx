import type { Metadata } from "next";
import Link from "next/link";
import { Archivo, Atkinson_Hyperlegible, IBM_Plex_Mono } from "next/font/google";
import deployments from "../../deployments/ink-sepolia.json";
import "./globals.css";

const archivo = Archivo({ subsets: ["latin"], variable: "--font-display" });
const atkinson = Atkinson_Hyperlegible({ subsets: ["latin"], weight: ["400", "700"], variable: "--font-body" });
const plexMono = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400", "600"], variable: "--font-mono" });

export const metadata: Metadata = {
  title: { default: "Cover · Build workspace", template: "%s · Cover" },
  description: "The shared starting point for covered agent purchases on Ink Sepolia.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body className={`${archivo.variable} ${atkinson.variable} ${plexMono.variable}`}>
        <a className="skip-link" href="#main">Skip to content</a>
        <header className="site-header">
          <Link className="wordmark" href="/" aria-label="Cover home">cover<span aria-hidden="true">.</span></Link>
          <nav aria-label="Main navigation">
            <Link href="/ana">Shopper</Link>
            <Link href="/maker">Maker</Link>
          </nav>
          <span className="network-label">Ink Sepolia / {deployments.chainId}</span>
        </header>
        <main id="main">{children}</main>
        <footer className="site-footer">Testnet only. Simulation is labelled throughout; mock evidence is never presented as onchain activity.</footer>
      </body>
    </html>
  );
}
