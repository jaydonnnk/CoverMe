import type { ServiceConfig } from "@/lib/types";

export function ModeBadge({ config }: { config: ServiceConfig | null }) {
  return <div className="mode-group"><span className={`badge ${config?.mode === "live" ? "good" : "warning"}`}>
    {!config ? "Connecting to service…" : config.mode === "fake" ? "Demo simulation" : "Ink Sepolia live"}
  </span>{config && <span className="small muted">{config.agent_mode === "scripted" ? "Scripted demo agent" : "OpenAI agent"}</span>}</div>;
}
