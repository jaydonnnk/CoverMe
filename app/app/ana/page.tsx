import type { Metadata } from "next";

export const metadata: Metadata = { title: "Shopper workspace" };

export default function ShopperPage() {
  return (
    <div className="workspace">
      <p className="eyebrow">01 / Francesco · Shopper scaffold</p>
      <h1>Ana’s purchase workspace.</h1>
      <p className="intro">The limits form, chat, sign card and purchase receipt will live here. Nothing is signed or submitted by this starter.</p>
      <p className="scaffold-note">Integration points: Jaydon’s app/lib/wallet.ts, POST /chat, POST /requests, GET /purchases/&#123;id&#125; and GET /events. See shared/INTERFACES.md.</p>
    </div>
  );
}
