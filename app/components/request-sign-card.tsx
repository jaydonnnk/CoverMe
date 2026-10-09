import type { AgentListing, PricingSnapshot, RequestDraft } from "@/lib/types";
import { usd } from "@/lib/format";

export function RequestSignCard({ draft, pricing, agent, shipping, busy, enabled, onSign }: { draft: RequestDraft; pricing: PricingSnapshot; agent: AgentListing; shipping: string; busy: boolean; enabled: boolean; onSign: () => void }) {
  return <section className="sign-card" aria-labelledby="review-heading"><div className="section-heading"><h3 id="review-heading">Review purchase request</h3><span className="badge warning">Awaiting your signature</span></div>
    <h4>{draft.item}</h4><p className="small">Hired: <strong>{agent.agent_name}</strong> by {agent.provider_name}</p><dl className="request-details"><div><dt>Shop</dt><dd>{draft.shop}</dd></div><div><dt>Colour</dt><dd>{draft.colour || "Any"}</dd></div><div><dt>Maximum</dt><dd className="mono">{usd(draft.maxUsdCents)}</dd></div><div><dt>Destination</dt><dd>{shipping}{draft.addressHash.startsWith("0xbbbb") && <strong className="danger-text"> · different address requested</strong>}</dd></div></dl>
    <div className="cost-breakdown"><div><span>Item subtotal</span><strong className="mono">{usd(pricing.item_subtotal_cents)}</strong></div><div><span>Shipping</span><strong className="mono">{usd(pricing.shipping_cents)}</strong></div><div><span>Tax</span><strong className="mono">{usd(pricing.tax_cents)}</strong></div><div><span>Agent service fee</span><strong className="mono">{usd(pricing.service_fee_cents)}</strong></div><div className="total"><span>Approved buyer total</span><strong className="mono">{usd(pricing.buyer_total_cents)}</strong></div><p className="small muted">Full approved total protected in this simulation. CoverMe’s risk fee is paid separately by the provider.</p></div>
    <button disabled={!enabled || busy} onClick={onSign}>{busy ? "Submitting request…" : "Sign request"}</button><span className="small muted beside">Simulated consent, not an EIP-712 signature</span>
  </section>;
}
