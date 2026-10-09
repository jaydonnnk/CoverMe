import Image from "next/image";
import type { Item, Purchase } from "@/lib/types";
import { failureLabel, short, usd, usdc } from "@/lib/format";

function ItemEvidence({ item, label }: { item: Item; label: string }) {
  return <div className="item-evidence"><span className="small muted">{label}</span>
    {item.image_url ? <Image unoptimized src={item.image_url} alt={`${item.item}, ${item.colour}`} width={120} height={90} /> : <div className={`swatch ${item.colour.includes("white") ? "dune" : "black"}`} aria-label={`${item.colour || "Unspecified"} colour swatch`} />}
    <h4>{item.item}</h4><p>{item.colour || "Any colour"}</p><p className="small muted">{item.shop}</p>
  </div>;
}

export function Receipt({ purchase: p, elapsed, claimBusy, onClaim }: { purchase: Purchase; elapsed: number | null; claimBusy: boolean; onClaim: () => void }) {
  if (p.status === "refused") return <section className="refusal" role="status"><h3>Purchase refused</h3><p className="large">No money moved.</p><ul>{p.failures.map(rule => <li key={rule}>{failureLabel(rule)}</li>)}</ul><p className="small">Every failed rule was checked before releasing funds.</p></section>;
  if (!p.bought || !["confirmed", "claimed", "refunded", "rejected"].includes(p.status)) return null;
  const mismatch = p.asked.colour && p.asked.colour !== p.bought.colour;
  return <section className={`receipt ${p.status === "refunded" ? "refund-complete" : ""}`} aria-labelledby={`receipt-${p.id}`}>
    <div className="section-heading"><h3 id={`receipt-${p.id}`}>Receipt #{p.id}</h3><span className={`badge ${p.status === "refunded" ? "good" : mismatch ? "warning" : "good"}`}>{p.status === "refunded" ? "Refunded" : mismatch ? "Item mismatch" : "Correct item"}</span></div>
    <div className="receipt-items"><ItemEvidence item={p.asked} label="You asked for" /><ItemEvidence item={p.bought} label="Agent bought" /></div>
    {mismatch && <p className="mismatch mono">{p.asked.colour} != {p.bought.colour}</p>}
    <div className="receipt-amount"><span>Listed price</span><strong className="mono">{usd(p.listed_usd_cents ?? 0)}</strong></div>
    {p.sandbox_pricing && <div className="receipt-amount"><span>Actual sandbox charge</span><strong className="mono">{usdc(p.charge_usdc ?? 0)}</strong></div>}
    {p.status === "confirmed" && mismatch && <button onClick={onClaim} disabled={claimBusy}>{claimBusy ? "Opening claim…" : "Wrong item"}</button>}
    {(claimBusy || p.status === "claimed") && <p className="claim-timer" role="status">Waiting for refund · <span className="mono">{((elapsed ?? 0) / 1000).toFixed(1)} s</span></p>}
    {p.status === "refunded" && <div className="refund-evidence" role="status"><p className="large">Refunded from the maker’s deposit{elapsed !== null ? ` in ${(elapsed / 1000).toFixed(1)} s` : ""}</p><p className="small">{p.simulation ? "Simulated refund · measured browser time · no money moved" : "Measured from claim click to refund event"}</p>{p.refund_tx_hash && <p className="mono small wrap">Evidence: {short(p.refund_tx_hash)}</p>}</div>}
    {p.status === "rejected" && <p>Claim rejected: purchased attributes match the request.</p>}
  </section>;
}
