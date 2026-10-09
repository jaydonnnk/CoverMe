"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import * as api from "@/lib/api";
import type { AgentListing, Limits, PricingSnapshot, Purchase, PurchaseEvent, RequestDraft, ServiceConfig } from "@/lib/types";
import { eventKey } from "@/lib/types";
import { AnaPanel } from "./ana-panel";
import type { Message } from "./chat-panel";
import { MakerPanel } from "./maker-panel";
import { Ledger } from "./ledger";
import { ModeBadge } from "./mode-badge";
import { AgentMarketplace } from "./agent-marketplace";

const errorText = (e: unknown) => e instanceof Error ? e.message : "Something went wrong. Please retry.";

export function DemoWorkspace({ view = "combined" }: { view?: "combined" | "ana" | "maker" }) {
  const [config, setConfig] = useState<ServiceConfig | null>(null);
  const [account, setAccount] = useState<string | null>(null);
  const [limitsSaved, setLimitsSaved] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState<RequestDraft | null>(null);
  const [agents, setAgents] = useState<AgentListing[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [pricing, setPricing] = useState<PricingSnapshot | null>(null);
  const [quoteId, setQuoteId] = useState<string | null>(null);
  const [failureInjected, setFailureInjected] = useState(false);
  const [currentId, setCurrentId] = useState<number | null>(null);
  const [purchases, setPurchases] = useState<Record<number, Purchase>>({});
  const [events, setEvents] = useState<PurchaseEvent[]>([]);
  const [connection, setConnection] = useState("Connecting…");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  const [claiming, setClaiming] = useState(false);
  const [elapsed, setElapsed] = useState<number | null>(null);
  const claimStart = useRef<{ id: number; at: number } | null>(null);
  const seen = useRef(new Set<string>());

  const refreshReceipt = useCallback(async (id: number) => {
    try { const p = await api.getPurchase(id); setPurchases(prev => ({ ...prev, [id]: p })); }
    catch (e) { setError(errorText(e)); }
  }, []);
  const loadConfig = useCallback(async () => {
    try { setConfig(await api.getConfig()); setError(""); }
    catch (e) { setError(errorText(e)); }
  }, []);
  const loadAgents = useCallback(async () => {
    try {
      const next = await api.getAgents(); setAgents(next);
      setSelectedAgentId(current => current && next.some(agent => agent.id === current) ? current : next[0]?.id || null);
    } catch (e) { setError(errorText(e)); }
  }, []);

  useEffect(() => {
    Promise.all([api.getConfig(), api.getAgents()]).then(([nextConfig, nextAgents]) => {
      setConfig(nextConfig); setAgents(nextAgents); setSelectedAgentId(nextAgents[0]?.id || null); setError("");
    }, e => setError(errorText(e)));
    const source = new EventSource(`${api.serviceUrl}/events`);
    source.onopen = () => setConnection("Connected");
    source.onerror = () => setConnection("Disconnected · reconnecting…");
    source.addEventListener("purchase", (message: MessageEvent) => {
      try {
        const event = JSON.parse(message.data) as PurchaseEvent;
        const key = eventKey(event);
        if (seen.current.has(key)) return;
        seen.current.add(key);
        setEvents(prev => [...prev, event].slice(-200));
        if (event.status === "error" && event.step !== "refused") setError(event.detail);
        if (["refunded", "rejected"].includes(event.step) && claimStart.current?.id === event.purchase_id) {
          setElapsed(performance.now() - claimStart.current.at);
          claimStart.current = null; setClaiming(false);
        }
        void refreshReceipt(event.purchase_id);
        if (["released", "confirmed", "refunded", "rejected", "score_written"].includes(event.step)) setRevision(prev => prev + 1);
      } catch { setError("Could not read a ledger event. Reconnect the service and retry."); }
    });
    return () => source.close();
  }, [loadConfig, refreshReceipt]);

  useEffect(() => {
    if (!claiming) return;
    const timer = setInterval(() => { if (claimStart.current) setElapsed(performance.now() - claimStart.current.at); }, 100);
    return () => clearInterval(timer);
  }, [claiming]);

  async function saveLimits(values: Limits) {
    if (config?.mode !== "fake") return;
    setBusy("limits"); setError("");
    try { await api.setDemoLimits(values); setLimitsSaved(true); setRevision(v => v + 1); }
    catch (e) { setError(errorText(e)); }
    finally { setBusy(""); }
  }
  async function chat(text: string) {
    if (!selectedAgentId) return;
    setBusy("chat"); setError("");
    setMessages(prev => [...prev, { role: "Ana", text }]);
    try {
      const result = await api.sendChat(text, selectedAgentId);
      setMessages(prev => [...prev, { role: "Agent", text: result.message }]);
      setDraft(result.request_draft);
      setPricing(result.pricing); setQuoteId(result.quote_id);
      setConfig(prev => prev ? { ...prev, agent_mode: result.mode } : prev);
    } catch (e) { setError(errorText(e)); }
    finally { setBusy(""); }
  }
  async function sign() {
    if (!draft || !account || !quoteId || config?.mode !== "fake") return;
    setBusy("sign"); setError("");
    const normalized = { ...draft, shopper: account, shop: draft.shop.toLowerCase(), colour: draft.colour.toLowerCase(), size: draft.size.toLowerCase(), model: draft.model.toLowerCase() };
    try {
      const { purchase_id } = await api.submitRequest(normalized, `mock:${account.toLowerCase()}`, quoteId);
      setCurrentId(purchase_id); setDraft(null); setPricing(null); setQuoteId(null); setElapsed(null);
      await refreshReceipt(purchase_id);
    } catch (e) { setError(errorText(e)); }
    finally { setBusy(""); }
  }
  async function claim() {
    if (!currentId || config?.mode !== "fake") return;
    claimStart.current = { id: currentId, at: performance.now() };
    setElapsed(0); setClaiming(true); setError("");
    try { await api.claimDemo(currentId); }
    catch (e) { claimStart.current = null; setClaiming(false); setElapsed(null); setError(errorText(e)); }
  }
  async function reset() {
    setBusy("reset"); setError("");
    try {
      await api.resetDemo();
      setDraft(null); setPricing(null); setQuoteId(null); setMessages([]); setEvents([]); seen.current.clear();
      setPurchases({}); setCurrentId(null); setLimitsSaved(false); setElapsed(null);
      setFailureInjected(false); claimStart.current = null; setClaiming(false); setRevision(v => v + 1); await loadAgents();
    } catch (e) { setError(errorText(e)); }
    finally { setBusy(""); }
  }
  const purchase = currentId ? purchases[currentId] || null : null;
  const selectedAgent = agents.find(agent => agent.id === selectedAgentId) || null;
  const inFlight = purchase && !["confirmed", "refused", "refunded", "rejected", "error"].includes(purchase.status);
  return <div className="workspace"><div className="workspace-heading"><div><h1>Hire an agent. Keep the protection.</h1><p className="muted small">Compare reputation and fees, approve the purchase, and hold the provider accountable.</p></div><ModeBadge config={config} /></div>
    <div className="workspace-tools"><span className="small muted">Testnet workspace · {config?.mode === "fake" ? "No real money moves" : "Live integration pending"}</span>{config?.mode === "fake" && <button className="secondary small" onClick={() => void reset()} disabled={!!busy || claiming || !!inFlight}>{busy === "reset" ? "Resetting…" : "Reset rehearsal"}</button>}</div>
    {error && <div className="notice danger-text" role="alert">{error}{!config && <button className="secondary small" onClick={() => void loadConfig()}>Retry connection</button>}</div>}
    {view !== "maker" && <AgentMarketplace agents={agents} selectedId={selectedAgentId} disabled={!!busy || !!draft || !!inFlight} onHire={id => { setSelectedAgentId(id); setDraft(null); setPricing(null); setQuoteId(null); setMessages([]); }} />}
    <div className={`workspace-grid ${view !== "combined" ? "single-panel" : ""}`}>
      {view !== "maker" && <AnaPanel config={config} agent={selectedAgent} pricing={pricing} account={account} busy={busy} limitsSaved={limitsSaved} messages={messages} draft={draft} purchase={purchase} events={events} elapsed={elapsed} claiming={claiming} onConnect={() => config?.mode === "fake" && setAccount(config.shopper)} onSave={saveLimits} onChat={chat} onSign={() => void sign()} onClaim={() => void claim()} />}
      {view !== "ana" && <MakerPanel config={config} revision={revision} agent={selectedAgent} failureInjected={failureInjected} onFailureChange={setFailureInjected} onProviderUpdated={() => { void loadAgents(); setRevision(v => v + 1); }} />}
    </div><Ledger events={events} connection={connection} />
  </div>;
}
