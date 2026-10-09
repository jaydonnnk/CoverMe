"use client";
import { useEffect, useRef, useState } from "react";
import deployments from "../../deployments/ink-sepolia.json";
import { getDemoMaker, setDemoProviderFee, setFailureMode } from "@/lib/api";
import type { AgentListing, MakerMetrics, ServiceConfig } from "@/lib/types";
import { usd, usdc } from "@/lib/format";

function ProviderControls({ agent, onSaved, onError }: { agent: AgentListing; onSaved: () => void; onError: (message: string) => void }) {
  const [feeType, setFeeType] = useState<"flat" | "percentage">(agent.fee_type);
  const [feeValue, setFeeValue] = useState(agent.fee_value);
  const [saving, setSaving] = useState(false);
  async function saveFee() {
    setSaving(true); onError("");
    try { await setDemoProviderFee(agent.id, feeType, feeValue); onSaved(); }
    catch (e) { onError(e instanceof Error ? e.message : "Could not update fee"); }
    finally { setSaving(false); }
  }
  return <div className="provider-controls"><label>Service fee model<select value={feeType} onChange={e => setFeeType(e.target.value as "flat" | "percentage")}><option value="flat">Fixed fee</option><option value="percentage">Percentage</option></select></label><label>{feeType === "flat" ? "Fee in cents" : "Basis points"}<input type="number" min="0" max="10000" value={feeValue} onChange={e => setFeeValue(Number(e.target.value))} /></label><button className="secondary small" disabled={saving} onClick={() => void saveFee()}>{saving ? "Saving…" : "Apply to new requests"}</button></div>;
}

export function MakerPanel({ config, revision, agent, failureInjected, onFailureChange, onProviderUpdated }: {
  config: ServiceConfig | null; revision: number; agent: AgentListing | null; failureInjected: boolean;
  onFailureChange: (enabled: boolean) => void; onProviderUpdated: () => void;
}) {
  const [metrics, setMetrics] = useState<MakerMetrics | null>(null);
  const [stale, setStale] = useState(false);
  const [error, setError] = useState("");
  const [changed, setChanged] = useState<string[]>([]);
  const previous = useRef<MakerMetrics | null>(null);

  useEffect(() => {
    if (config?.mode !== "fake" || !agent) return;
    let cancelled = false;
    let pending = false;
    const poll = async () => {
      if (pending) return; pending = true;
      try {
        const next = await getDemoMaker(agent.id);
        if (!cancelled) {
          const last = previous.current;
          setChanged(last ? Object.keys(next).filter(key => next[key as keyof MakerMetrics] !== last[key as keyof MakerMetrics]) : []);
          previous.current = next; setMetrics(next); setStale(false); setError("");
        }
      } catch (e) { if (!cancelled) { setStale(true); setError(e instanceof Error ? e.message : "Provider read failed"); } }
      finally { pending = false; }
    };
    void poll(); const interval = setInterval(() => void poll(), 4500);
    return () => { cancelled = true; clearInterval(interval); };
  }, [agent, config?.mode, revision]);

  async function toggleFailure() {
    try { const next = !failureInjected; await setFailureMode(next); onFailureChange(next); }
    catch (e) { setError(e instanceof Error ? e.message : "Could not change rehearsal mode"); }
  }
  const rows: [string, keyof MakerMetrics, (v: number) => string][] = [
    ["Provider deposit", "maker_deposit", usdc], ["Reserved cover", "reserved_cover", usdc],
    ["Free cover", "free_cover", usdc], ["Score average", "score_average", v => `${v} / 100`],
    ["Final outcomes", "score_count", String], ["CoverMe fee", "fee_bps", v => `${v / 100}%`],
    ["Auto-pay limit", "auto_pay_limit_cents", usd], ["Fees paid to CoverMe", "fees_paid", usdc],
    ["Agent earnings", "service_earnings", usdc], ["Provider refund loss", "provider_loss", usdc],
  ];
  return <aside className="maker-panel" aria-labelledby="maker-heading"><div className="panel-title"><h2 id="maker-heading">Provider setup</h2><span className="badge warning">Demo KYB · simulated</span></div>
    <div className="agent-identity"><div className="agent-mark" aria-hidden="true">{agent?.agent_name[0] || "C"}</div><div><h3>{agent?.agent_name || "Hire an agent"}</h3><p className="small muted">{agent?.provider_name || "Select a marketplace listing"}</p><p className="mono small">ERC-8004 #{agent?.erc8004_agent_id ?? "simulated"}</p></div></div>
    {agent && <ProviderControls key={agent.id} agent={agent} onSaved={onProviderUpdated} onError={setError} />}
    <div className={`failure-control ${failureInjected ? "active" : ""}`}><div><strong>Injected agent failure</strong><p className="small muted">Off: known colour mismatches stop before payment. On: the PowerBug rehearsal records White/Dune so you can show the refund.</p></div><button className={failureInjected ? "" : "secondary"} onClick={() => void toggleFailure()}>{failureInjected ? "Failure armed" : "Arm rehearsal"}</button></div>
    <dl className="metrics">{rows.map(([label, key, format]) => <div key={key}><dt>{label}</dt><dd key={`${key}-${metrics?.[key]}`} className={`mono ${changed.includes(key) ? "metric-changed" : ""}`}>{config?.mode === "live" ? "Adapter pending" : metrics ? format(Number(metrics[key])) : <span className="skeleton" aria-label="Loading metric" />}</dd></div>)}</dl>
    {metrics?.merchant_recovery_status === "pending" && <p className="notice warning-text"><strong>Merchant recovery pending</strong><span className="small">Provider handles the vendor return separately.</span></p>}
    {stale && <p className="warning-text small" role="status">Stale values · {error}</p>}{error && !stale && <p className="danger-text small" role="alert">{error}</p>}
    <div className="cover-note"><h3>The provider bears covered mistakes.</h3><p className="small">CoverMe refunds the approved buyer total from prefunded collateral. Vendor recovery stays with the provider.</p></div>
    <p className="small muted">Identity registry: {deployments.registries.Identity.address}</p>
  </aside>;
}
