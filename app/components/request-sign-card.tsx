import type { RequestDraft } from "@/lib/types";
import { usd } from "@/lib/format";

export function RequestSignCard({ draft, shipping, busy, enabled, onSign }: { draft: RequestDraft; shipping: string; busy: boolean; enabled: boolean; onSign: () => void }) {
  return <section className="sign-card" aria-labelledby="review-heading"><div className="section-heading"><h3 id="review-heading">Review purchase request</h3><span className="badge warning">Awaiting your signature</span></div>
    <h4>{draft.item}</h4><dl className="request-details"><div><dt>Shop</dt><dd>{draft.shop}</dd></div><div><dt>Colour</dt><dd>{draft.colour || "Any"}</dd></div><div><dt>Maximum</dt><dd className="mono">{usd(draft.maxUsdCents)}</dd></div><div><dt>Destination</dt><dd>{shipping}{draft.addressHash.startsWith("0xbbbb") && <strong className="danger-text"> · different address requested</strong>}</dd></div></dl>
    <button disabled={!enabled || busy} onClick={onSign}>{busy ? "Submitting request…" : "Sign request"}</button><span className="small muted beside">Simulated consent, not an EIP-712 signature</span>
  </section>;
}
