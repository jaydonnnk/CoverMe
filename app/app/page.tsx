import Link from "next/link";

export default function Home() {
  return (
    <div className="workspace">
      <p className="eyebrow">Reap × 65labs / Build workspace</p>
      <h1>Give agents room to act.<br /><em>Keep the purchase covered.</em></h1>
      <p className="intro">A shared foundation for Jaydon and Francesco. The contracts, payment guard, service and screens have separate homes; the interfaces are shared.</p>
      <div className="workspace-grid">
        <Link className="workspace-link" href="/ana">
          <span className="eyebrow">01 / Shopper workspace</span>
          <h2>Ana’s purchase</h2>
          <p>Limits, chat, a signed request and a receipt. Ready for Francesco’s screens.</p>
          <span className="link-label">Open shopper scaffold <span aria-hidden="true">↗</span></span>
        </Link>
        <Link className="workspace-link" href="/maker">
          <span className="eyebrow">02 / Maker workspace</span>
          <h2>The agent’s cover</h2>
          <p>Identity, deposits, reserved cover and reputation. Waiting for deployed contracts.</p>
          <span className="link-label">Open maker scaffold <span aria-hidden="true">↗</span></span>
        </Link>
      </div>
      <p className="scaffold-note">Foundation only · Wallet and payment integrations are intentionally not implemented.</p>
    </div>
  );
}
