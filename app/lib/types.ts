export type Step = "checked" | "refused" | "needs_approval" | "released" | "fee_taken" | "funded" | "paid" | "confirmed" | "claimed" | "refunded" | "rejected" | "needs_review" | "score_written";
export type PurchaseEvent = {
  purchase_id: number; step: Step; status: "ok" | "waiting" | "error";
  tx_hash: string | null; kwal_payment_id: string | null; detail: string; ts: string;
};
export type RequestDraft = {
  shopper: string; agentId: string; shop: string; item: string; colour: string;
  size: string; model: string; maxUsdCents: number; addressHash: string;
  nonce: string; deadline: string;
};
export type Item = { shop: string; item: string; colour: string; size: string; model: string; image_url: string | null };
export type Purchase = {
  id: number; agent_id: string; status: string; asked: Item; bought: Item | null;
  listed_usd_cents: number | null; charge_usdc: number | null; sandbox_pricing: boolean;
  tx_hash: string | null; refund_tx_hash: string | null; kwal_payment_id: string | null;
  onchain_purchase_id: number | null; simulation: boolean; failures: string[];
  agent_listing_id: string | null; provider_name: string | null; agent_name: string | null;
  fee_type: "flat" | "percentage" | null; fee_value: number | null; service_fee_cents: number;
  shipping_cents: number; tax_cents: number;
  buyer_total_cents: number | null; refundable_usdc: number | null; refund_amount_usdc: number | null;
  merchant_recovery_status: "not_applicable" | "pending"; failure_injected: boolean;
};
export type AgentListing = {
  id: string; provider_name: string; agent_name: string; erc8004_agent_id: string | null;
  score_average: number | null; score_count: number; fee_type: "flat" | "percentage";
  fee_value: number; coverage_limit_usdc: number; kyb_status: "demo_verified" | "not_verified";
  endpoint_status: "scripted" | "connected"; executable: boolean; simulation: boolean;
};
export type PricingSnapshot = {
  quote_id: string; agent_listing_id: string; item: string; shop: string;
  fee_type: "flat" | "percentage"; fee_value: number; item_subtotal_cents: number;
  shipping_cents: number; tax_cents: number; service_fee_cents: number;
  buyer_total_cents: number; refundable_usdc: number;
};
export type ChatResponse = { message: string; request_draft: RequestDraft | null; mode: "scripted" | "openai"; quote_id: string | null; agent_listing_id: string | null; pricing: PricingSnapshot | null };
export type ServiceConfig = {
  mode: "fake" | "live"; agent_mode: "scripted" | "openai"; shopper: string;
  address_hash: string; shipping_summary: string; live_wallet_available: boolean;
};
export type Limits = { per_item_max_cents: number; monthly_max_cents: number; shops: string[]; ends_at: number };
export type MakerMetrics = {
  agent_id: string; listing_id: string; provider_name: string; agent_name: string;
  maker_deposit: number; reserved_cover: number; free_cover: number;
  score_average: number; score_count: number; fee_bps: number; auto_pay_limit_cents: number; fees_paid: number;
  service_fee_type: "flat" | "percentage"; service_fee_value: number; service_earnings: number;
  provider_loss: number; merchant_recovery_status: "not_applicable" | "pending";
};
export const eventKey = (e: PurchaseEvent) => `${e.purchase_id}:${e.step}:${e.ts}:${e.tx_hash ?? ""}`;
