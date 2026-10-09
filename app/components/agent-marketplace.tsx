import type { AgentListing } from "@/lib/types";
import { usdc } from "@/lib/format";

function fee(agent: AgentListing) {
  return agent.fee_type === "flat" ? `$${(agent.fee_value / 100).toFixed(2)} / purchase` : `${agent.fee_value / 100}% of item`;
}

export function AgentMarketplace({ agents, selectedId, disabled, onHire }: { agents: AgentListing[]; selectedId: string | null; disabled: boolean; onHire: (id: string) => void }) {
  return <section className="marketplace" aria-labelledby="marketplace-heading">
    <div className="marketplace-copy"><p className="small muted">Shopping-agent marketplace</p><h2 id="marketplace-heading">Choose who shops for you.</h2><p className="muted">Compare track record, price and provider-backed coverage before you hire.</p></div>
    <div className="agent-listings">{agents.map(agent => {
      const selected = selectedId === agent.id;
      return <article className={`agent-listing ${selected ? "selected" : ""}`} key={agent.id}>
        <div className="section-heading"><div><h3>{agent.agent_name}</h3><p className="small muted">by {agent.provider_name}</p></div><span className="badge good">Demo KYB</span></div>
        <dl className="listing-facts"><div><dt>Reputation</dt><dd className="mono">{agent.score_count ? `${agent.score_average}/100` : "Unrated"}</dd></div><div><dt>Final outcomes</dt><dd className="mono">{agent.score_count}</dd></div><div><dt>Agent fee</dt><dd>{fee(agent)}</dd></div><div><dt>Available coverage</dt><dd className="mono">{usdc(agent.coverage_limit_usdc)}</dd></div></dl>
        <p className="small muted">{agent.erc8004_agent_id !== null ? `ERC-8004 #${agent.erc8004_agent_id}` : "Comparison agent · simulated identity"} · {agent.endpoint_status === "connected" ? "Endpoint connected" : "Scripted endpoint"}</p>
        <button className={selected ? "secondary" : ""} disabled={disabled || selected} onClick={() => onHire(agent.id)}>{selected ? "Hired" : "Hire agent"}</button>
      </article>;
    })}</div>
  </section>;
}
