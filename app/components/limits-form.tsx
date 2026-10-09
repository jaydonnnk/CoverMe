"use client";
import { useState } from "react";
import type { Limits } from "@/lib/types";

const shops = ["keychron.com", "twelvesouth.com", "satechi.net", "zmdesktop.com", "gymshark.com"];

export function LimitsForm({ enabled, shipping, busy, saved, onSave }: {
  enabled: boolean; shipping: string; busy: boolean; saved: boolean; onSave: (limits: Limits) => Promise<void>;
}) {
  const [monthly, setMonthly] = useState("150");
  const [perItem, setPerItem] = useState("100");
  const [allowed, setAllowed] = useState(shops);
  const [end, setEnd] = useState("2026-10-31");
  return <form onSubmit={e => { e.preventDefault(); void onSave({ monthly_max_cents: Math.round(Number(monthly) * 100), per_item_max_cents: Math.round(Number(perItem) * 100), shops: allowed, ends_at: Math.floor(new Date(`${end}T23:59:59Z`).getTime() / 1000) }); }}>
    <div className="section-heading"><h3>Spending limits</h3><span className={`small ${saved ? "good-text" : "muted"}`}>{saved ? "Limits confirmed" : "Not set yet"}</span></div>
    <div className="form-grid">
      <label>Monthly maximum ($)<input type="number" min="0" step="0.01" required value={monthly} onChange={e => setMonthly(e.target.value)} /></label>
      <label>Per-item maximum ($)<input type="number" min="0" step="0.01" required value={perItem} onChange={e => setPerItem(e.target.value)} /></label>
    </div>
    <fieldset><legend>Allowed shops</legend><div className="shop-options">{shops.map(shop => <label className="check-label" key={shop}><input type="checkbox" checked={allowed.includes(shop)} onChange={e => setAllowed(e.target.checked ? [...allowed, shop] : allowed.filter(s => s !== shop))} />{shop}</label>)}</div></fieldset>
    <div className="form-grid"><div><span className="field-label">Shipping address</span><p className="small">{shipping}</p><p className="small muted">Saved server-side. The agent cannot replace it.</p></div><label>End date<input type="date" required value={end} onChange={e => setEnd(e.target.value)} /></label></div>
    <button disabled={!enabled || busy} type="submit">{busy ? "Setting limits…" : "Set limits"}</button>
    <span className="small muted beside">Simulation only · no wallet transaction</span>
  </form>;
}
