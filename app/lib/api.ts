import type { AgentListing, ChatResponse, Limits, MakerMetrics, Purchase, RequestDraft, ServiceConfig } from "./types";

export const serviceUrl = (process.env.NEXT_PUBLIC_SERVICE_URL || "http://localhost:8000").replace(/\/$/, "");

async function request<T>(path: string, body?: unknown): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${serviceUrl}${path}`, {
      method: body === undefined ? "GET" : "POST",
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body), cache: "no-store",
    });
  } catch {
    throw new Error("Cannot reach the Cover service. Check that it is running, then retry.");
  }
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : `Request failed (${response.status}). Please retry.`);
  return data as T;
}

export const getConfig = () => request<ServiceConfig>("/config");
export const getAgents = () => request<AgentListing[]>("/agents");
export const sendChat = (message: string, agentListingId: string) => request<ChatResponse>("/chat", { message, agent_listing_id: agentListingId });
export const submitRequest = (draft: RequestDraft, signature: string, quoteId: string) => request<{ purchase_id: number }>("/requests", { request: draft, signature, quote_id: quoteId });
export const getPurchase = (id: number) => request<Purchase>(`/purchases/${id}`);
// These helpers intentionally cannot be used as a live wallet replacement.
export const setDemoLimits = (limits: Limits) => request("/demo/limits", limits);
export const getDemoMaker = (agentListingId: string) => request<MakerMetrics>(`/demo/maker?agent_listing_id=${encodeURIComponent(agentListingId)}`);
export const setDemoProviderFee = (agentListingId: string, feeType: "flat" | "percentage", feeValue: number) => request<MakerMetrics>(`/demo/providers/${encodeURIComponent(agentListingId)}`, { fee_type: feeType, fee_value: feeValue });
export const setFailureMode = (enabled: boolean) => request<{ enabled: boolean }>("/demo/failure-mode", { enabled });
export const claimDemo = (id: number) => request(`/demo/claims/${id}`, {});
export const resetDemo = () => request("/demo/reset", {});
