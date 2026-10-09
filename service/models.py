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


class ChatResponse(BaseModel):
    message: str
    request_draft: RequestDraft | None = None
    mode: Literal["scripted", "openai"]


class SignedPurchaseRequest(BaseModel):
    request: RequestDraft
    signature: str = Field(min_length=1)


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
