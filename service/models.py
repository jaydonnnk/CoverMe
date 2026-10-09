"""Small API shapes; signed field names match shared/purchase-request.json."""
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Step = Literal["checked", "refused", "needs_approval", "released", "fee_taken", "funded", "paid", "confirmed", "claimed", "refunded", "rejected", "needs_review", "score_written"]


class Event(BaseModel):
    purchase_id: int
    step: Step
    status: Literal["ok", "waiting", "error"] = "ok"
    tx_hash: str | None = None
    kwal_payment_id: str | None = None
    detail: str
    ts: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"))


class RequestDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    shopper: str = Field(pattern=r"^0x[0-9a-fA-F]{40}$")
    agentId: str = Field(pattern=r"^[0-9]+$")
    shop: str
    item: str
    colour: str = ""
    size: str = ""
    model: str = ""
    maxUsdCents: int = Field(gt=0)
    addressHash: str = Field(pattern=r"^0x[0-9a-fA-F]{64}$")
    nonce: str = Field(pattern=r"^[0-9]+$")
    deadline: str = Field(pattern=r"^[0-9]+$")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    agent_listing_id: str = Field(default="atlas", min_length=1, max_length=80)


class AgentListing(BaseModel):
    id: str
    provider_name: str
    agent_name: str
    erc8004_agent_id: str | None = None
    score_average: int | None = Field(default=None, ge=0, le=100)
    score_count: int = Field(default=0, ge=0)
    fee_type: Literal["flat", "percentage"]
    fee_value: int = Field(ge=0)
    coverage_limit_usdc: int = Field(ge=0)
    kyb_status: Literal["demo_verified", "not_verified"]
    endpoint_status: Literal["scripted", "connected"]
    executable: bool = True
    simulation: bool = True


class PricingSnapshot(BaseModel):
    quote_id: str
    agent_listing_id: str
    item: str
    shop: str
    fee_type: Literal["flat", "percentage"]
    fee_value: int = Field(ge=0)
    item_subtotal_cents: int = Field(ge=0)
    shipping_cents: int = Field(default=0, ge=0)
    tax_cents: int = Field(default=0, ge=0)
    service_fee_cents: int = Field(ge=0)
    buyer_total_cents: int = Field(ge=0)
    refundable_usdc: int = Field(ge=0)


class ChatResponse(BaseModel):
    message: str
    request_draft: RequestDraft | None = None
    mode: Literal["scripted", "openai"]
    quote_id: str | None = None
    agent_listing_id: str | None = None
    pricing: PricingSnapshot | None = None


class SignedPurchaseRequest(BaseModel):
    request: RequestDraft
    signature: str = Field(min_length=1)
    quote_id: str | None = None


class AskedItem(BaseModel):
    shop: str
    item: str
    colour: str = ""
    size: str = ""
    model: str = ""
    image_url: str | None = None


class BoughtItem(AskedItem):
    pass


class Purchase(BaseModel):
    id: int
    agent_id: str
    status: str = "waiting"
    asked: AskedItem
    bought: BoughtItem | None = None
    listed_usd_cents: int | None = None
    charge_usdc: int | None = None
    sandbox_pricing: bool = False
    tx_hash: str | None = None
    refund_tx_hash: str | None = None
    kwal_payment_id: str | None = None
    onchain_purchase_id: int | None = None
    simulation: bool
    failures: list[str] = Field(default_factory=list)
    agent_listing_id: str | None = None
    provider_name: str | None = None
    agent_name: str | None = None
    fee_type: Literal["flat", "percentage"] | None = None
    fee_value: int | None = None
    service_fee_cents: int = 0
    shipping_cents: int = 0
    tax_cents: int = 0
    buyer_total_cents: int | None = None
    refundable_usdc: int | None = None
    refund_amount_usdc: int | None = None
    merchant_recovery_status: Literal["not_applicable", "pending"] = "not_applicable"
    failure_injected: bool = False
