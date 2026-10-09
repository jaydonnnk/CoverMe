import type { Metadata } from "next";
import Link from "next/link";
import deployments from "../../deployments/ink-sepolia.json";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Cover · Build workspace", template: "%s · Cover" },
  description: "The shared starting point for covered agent purchases on Ink Sepolia.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>
        <a className="skip-link" href="#main">Skip to content</a>
        <header className="site-header">
          <Link className="wordmark" href="/" aria-label="Cover home">cover<span aria-hidden="true">.</span></Link>
          <nav aria-label="Main navigation">
            <Link href="/ana">Shopper</Link>
            <Link href="/maker">Maker</Link>
          </nav>
          <span className="network-label">Ink Sepolia / {deployments.chainId} · Scaffold</span>
        </header>
        <main id="main">{children}</main>
        <footer className="site-footer">Testnet only. No wallets connected. No money moves.</footer>
      </body>
    </html>
  );
}
