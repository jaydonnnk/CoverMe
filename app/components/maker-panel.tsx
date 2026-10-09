"use client";
import { useEffect, useRef, useState } from "react";
import deployments from "../../deployments/ink-sepolia.json";
import { getDemoMaker } from "@/lib/api";
import type { MakerMetrics, ServiceConfig } from "@/lib/types";
import { usd, usdc } from "@/lib/format";

export function MakerPanel({ config, revision }: { config: ServiceConfig | null; revision: number }) {
  const [metrics, setMetrics] = useState<MakerMetrics | null>(null);
  const [stale, setStale] = useState(false);
  const [error, setError] = useState("");
  const [changed, setChanged] = useState<string[]>([]);
  const previous = useRef<MakerMetrics | null>(null);
  useEffect(() => {
    if (config?.mode !== "fake") return;
    let cancelled = false;
    let pending = false;
    const poll = async () => {
      if (pending) return;
      pending = true;
      try {
        const next = await getDemoMaker();
        if (!cancelled) {
          const last = previous.current;
          setChanged(last ? Object.keys(next).filter(key => next[key as keyof MakerMetrics] !== last[key as keyof MakerMetrics]) : []);
          previous.current = next;
          setMetrics(next); setStale(false); setError("");
        }
      } catch (e) { if (!cancelled) { setStale(true); setError(e instanceof Error ? e.message : "Maker read failed"); } }
      finally { pending = false; }
    };
    void poll();
    const interval = setInterval(() => void poll(), 4500);
    return () => { cancelled = true; clearInterval(interval); };
  }, [config?.mode, revision]);
  const rows: [string, keyof MakerMetrics, (v: number) => string][] = [
    ["Maker deposit", "maker_deposit", usdc], ["Reserved cover", "reserved_cover", usdc],
    ["Free cover", "free_cover", usdc], ["Score average", "score_average", v => `${v} / 100`],
    ["Score count", "score_count", String], ["Fee rate", "fee_bps", v => `${v / 100}%`],
    ["Auto-pay limit", "auto_pay_limit_cents", usd], ["Fees paid to Cover", "fees_paid", usdc],
  ];
  return <aside className="maker-panel" aria-labelledby="maker-heading"><div className="panel-title"><h2 id="maker-heading">Maker’s cover</h2><span className="small muted">Refreshes every 4.5 s</span></div>
    <div className="agent-identity"><div className="agent-mark" aria-hidden="true">C</div><div><h3>Cover shopping agent</h3><p className="mono small">ERC-8004 #{config?.mode === "fake" ? "1 · simulated" : deployments.registries.agentId || "Not registered"}</p></div></div>
    {config?.mode === "fake" && <p className="small muted">Simulated deposit and score. Not onchain data.</p>}
    <dl className="metrics">{rows.map(([label, key, format]) => <div key={key}><dt>{label}</dt><dd key={`${key}-${metrics?.[key]}`} className={`mono ${changed.includes(key) ? "metric-changed" : ""}`}>
      {config?.mode === "live" ? "Not deployed / adapter pending" : metrics ? format(Number(metrics[key])) : <span className="skeleton" aria-label="Loading metric" />}
    </dd></div>)}</dl>
    {stale && <p className="warning-text small" role="status">Stale values · {error}</p>}
    <div className="cover-note"><h3>The maker backs the outcome.</h3><p className="small">A wrong item refunds Ana from the maker’s deposit and lowers the agent’s score.</p><p className="small muted">Lower score → higher fee, lower auto-pay limit.</p></div>
    <p className="small muted">Identity registry: {deployments.registries.Identity.address || "Not deployed"}</p>
  </aside>;
}
