import type { AgentListing, PricingSnapshot, Purchase, PurchaseEvent, RequestDraft, ServiceConfig, Limits } from "@/lib/types";
import { short } from "@/lib/format";
import { ChatPanel, type Message } from "./chat-panel";
import { LimitsForm } from "./limits-form";
import { RequestSignCard } from "./request-sign-card";
import { PurchaseProgress } from "./purchase-progress";
import { Receipt } from "./receipt";

export type AnaPanelProps = {
  config: ServiceConfig | null; account: string | null; busy: string; limitsSaved: boolean;
  messages: Message[]; draft: RequestDraft | null; purchase: Purchase | null; events: PurchaseEvent[];
  agent: AgentListing | null; pricing: PricingSnapshot | null;
  elapsed: number | null; claiming: boolean; onConnect: () => void; onSave: (values: Limits) => Promise<void>;
  onChat: (text: string) => Promise<void>; onSign: () => void; onClaim: () => void;
};

export function AnaPanel(props: AnaPanelProps) {
  const { config, account, busy, limitsSaved, messages, draft, purchase, events } = props;
  const enabled = config?.mode === "fake" && !!account;
  return <section className="ana-panel" aria-labelledby="ana-heading"><div className="panel-title"><h2 id="ana-heading">Ana’s workspace</h2><button className="secondary small" disabled={!config || !!busy || !!account || config.mode !== "fake"} onClick={props.onConnect}>{account ? short(account) : "Connect wallet"}</button></div>
    {config?.mode === "fake" && <p className="small muted">Connect uses a demo account. Sign and claim actions are simulations.</p>}
    {config?.mode === "live" && <p className="notice warning-text">Jaydon’s wallet adapter is not yet available. Live signing and transactions are disabled.</p>}
    <LimitsForm enabled={enabled && !busy} shipping={config?.shipping_summary || "Loading saved address…"} busy={busy === "limits"} saved={limitsSaved} onSave={props.onSave} />
    <ChatPanel enabled={enabled && !!props.agent && limitsSaved && !busy && !props.claiming && !draft && (!purchase || ["confirmed", "refused", "refunded", "rejected", "error"].includes(purchase.status))} messages={messages} busy={busy === "chat"} onSend={props.onChat} />
    {draft && props.pricing && props.agent && <RequestSignCard draft={draft} pricing={props.pricing} agent={props.agent} shipping={config?.shipping_summary || "Saved address"} enabled={enabled && limitsSaved && !busy} busy={busy === "sign"} onSign={props.onSign} />}
    <PurchaseProgress purchase={purchase} events={events} />
    {purchase && <Receipt purchase={purchase} elapsed={props.elapsed} claimBusy={props.claiming} onClaim={props.onClaim} />}
  </section>;
}
