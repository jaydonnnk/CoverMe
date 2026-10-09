import type { Metadata } from "next";

export const metadata: Metadata = { title: "Maker workspace" };

export default function MakerPage() {
  return (
    <div className="workspace">
      <p className="eyebrow">02 / Francesco · Maker scaffold</p>
      <h1>The agent’s cover workspace.</h1>
      <p className="intro">Agent identity, deposit, reserved cover, free cover, score, fee rate, auto-pay limit and fees paid will live here. No balances or scores are simulated.</p>
      <p className="scaffold-note">Integration points: Jaydon’s app/lib/wallet.ts and deployments/ink-sepolia.json. Addresses and ABIs are empty until deployment.</p>
    </div>
  );
}
