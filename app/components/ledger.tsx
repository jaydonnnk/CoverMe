"use client";
import { useEffect, useRef } from "react";
import type { PurchaseEvent } from "@/lib/types";
import { eventKey } from "@/lib/types";
import { short } from "@/lib/format";

export function Ledger({ events, connection }: { events: PurchaseEvent[]; connection: string }) {
  const viewport = useRef<HTMLDivElement>(null);
  const nearBottom = useRef(true);
  useEffect(() => { if (nearBottom.current && viewport.current) viewport.current.scrollTop = viewport.current.scrollHeight; }, [events.length]);
  return <section className="ledger" aria-labelledby="ledger-heading"><div className="panel-title"><h2 id="ledger-heading">Live ledger</h2><span className={`small ${connection === "Connected" ? "good-text" : "warning-text"}`} role="status">{connection} · {events.length} events</span></div>
    <div className="ledger-scroll" ref={viewport} onScroll={() => { const el = viewport.current; if (el) nearBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 60; }} tabIndex={0} aria-label="Scrollable purchase ledger">
      {!events.length ? <p className="empty-state">No events yet. Set limits, then submit your first purchase request.</p> : <table><caption className="sr-only">Purchase event evidence</caption><thead><tr><th>Time / purchase</th><th>Step</th><th>Detail</th><th>Status</th><th>Evidence</th></tr></thead><tbody>{events.map(e => <tr key={eventKey(e)}><td className="mono"><time dateTime={e.ts}>{new Date(e.ts).toLocaleTimeString("en-GB")}</time><span className="muted"> #{e.purchase_id}</span></td><td>{e.step.replaceAll("_", " ")}</td><td>{e.detail}</td><td><span className={`badge ${e.status === "ok" ? "good" : e.status === "error" ? "danger" : "warning"}`}>{e.status}</span></td><td className="mono small wrap">{e.tx_hash ? short(e.tx_hash) : "—"}{e.kwal_payment_id && <span className="payment-id">{e.kwal_payment_id}</span>}</td></tr>)}</tbody></table>}
    </div>
  </section>;
}
