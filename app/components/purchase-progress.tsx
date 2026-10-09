import type { Purchase, PurchaseEvent } from "@/lib/types";
import { short } from "@/lib/format";

export function PurchaseProgress({ purchase, events }: { purchase: Purchase | null; events: PurchaseEvent[] }) {
  if (!purchase) return null;
  if (purchase.status === "refused") return null;
  const steps = ["checked", "released", "funded", "paid", "confirmed"];
  return <section className="progress-block"><div className="section-heading"><h3>Purchase #{purchase.id}</h3><span className="small mono">{purchase.status.replaceAll("_", " ")}</span></div>
    <ol className="progress-steps">{steps.map(step => <li key={step} className={events.some(e => e.purchase_id === purchase.id && e.step === step && e.status === "ok") ? "complete" : "waiting"}>{step}</li>)}</ol>
    {purchase.tx_hash && <p className="small mono wrap">Transaction: {short(purchase.tx_hash)}</p>}
    {purchase.kwal_payment_id && <p className="small mono wrap">Kwal: {purchase.kwal_payment_id}</p>}
  </section>;
}
