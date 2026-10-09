"""Mock-only controls. No keys, wallet operations or onchain claims here."""
import hashlib
import json
from typing import Literal

from pydantic import BaseModel, Field

from service.guard import Limits
from service.models import AgentListing

SHOPPER = "0x" + "a" * 40
SHIP_TO = dict(name="Ana (simulation)", line1="Demo address", city="Singapore", postal_code="018956", country="SG", email="ana@example.invalid")
ADDRESS_HASH = "0x" + hashlib.sha256(json.dumps(SHIP_TO, sort_keys=True).encode()).hexdigest()


class DemoLimits(BaseModel):
    per_item_max_cents: int = Field(default=10000, ge=0)
    monthly_max_cents: int = Field(default=15000, ge=0)
    shops: list[str] = Field(default_factory=lambda: ["keychron.com", "twelvesouth.com", "satechi.net", "zmdesktop.com", "gymshark.com"])
    ends_at: int = 1793491200


class ProviderFeeUpdate(BaseModel):
    fee_type: Literal["flat", "percentage"]
    fee_value: int = Field(ge=0, le=10000)


class FailureMode(BaseModel):
    enabled: bool


class DemoState:
    def __init__(self):
        self.reset()

    def reset(self):
        self.limits = Limits()  # Set limits explicitly before buying.
        self.agents = {
            "atlas": dict(
                provider_name="Northstar Commerce", agent_name="Atlas Shopper",
                erc8004_agent_id="0", score_total=17664, score_count=184,
                fee_type="flat", fee_value=350, deposit=500_000_000,
                reserved=0, fees_paid=0, service_earnings=0, provider_loss=0,
                merchant_recovery_status="not_applicable", endpoint_status="scripted",
            ),
            "scout": dict(
                provider_name="Daybreak Agents", agent_name="Scout Buyer",
                erc8004_agent_id=None, score_total=3276, score_count=42,
                fee_type="percentage", fee_value=200, deposit=250_000_000,
                reserved=0, fees_paid=0, service_earnings=0, provider_loss=0,
                merchant_recovery_status="not_applicable", endpoint_status="scripted",
            ),
        }
        self.failure_injection = False
        self.claiming: set[int] = set()

    def set_limits(self, values: DemoLimits):
        self.limits = Limits(**values.model_dump(), address_hash=ADDRESS_HASH,
                             spent_this_month_cents=self.limits.spent_this_month_cents)

    def listing(self, listing_id: str):
        if listing_id not in self.agents:
            raise KeyError(f"Unknown agent listing: {listing_id}")
        return self.agents[listing_id]

    def listings(self):
        result = []
        for listing_id, agent in self.agents.items():
            count = agent["score_count"]
            result.append(AgentListing(
                id=listing_id, provider_name=agent["provider_name"], agent_name=agent["agent_name"],
                erc8004_agent_id=agent["erc8004_agent_id"],
                score_average=agent["score_total"] // count if count else None, score_count=count,
                fee_type=agent["fee_type"], fee_value=agent["fee_value"],
                coverage_limit_usdc=agent["deposit"] - agent["reserved"],
                kyb_status="demo_verified", endpoint_status=agent["endpoint_status"],
                executable=True, simulation=True,
            ))
        return result

    def set_fee(self, listing_id: str, values: ProviderFeeUpdate):
        agent = self.listing(listing_id)
        agent["fee_type"], agent["fee_value"] = values.fee_type, values.fee_value

    def metrics(self, listing_id: str = "atlas"):
        agent = self.listing(listing_id)
        count = agent["score_count"]
        avg = agent["score_total"] // count if count else 0
        return dict(
            agent_id=agent["erc8004_agent_id"] or "unregistered", listing_id=listing_id,
            provider_name=agent["provider_name"], agent_name=agent["agent_name"],
            maker_deposit=agent["deposit"], reserved_cover=agent["reserved"],
            free_cover=agent["deposit"] - agent["reserved"], score_average=avg,
            score_count=count, fee_bps=50 + 5 * (100 - avg),
            auto_pay_limit_cents=self.limits.per_item_max_cents if avg >= 90 else (5000 if avg >= 60 else 0),
            fees_paid=agent["fees_paid"], service_fee_type=agent["fee_type"],
            service_fee_value=agent["fee_value"], service_earnings=agent["service_earnings"],
            provider_loss=agent["provider_loss"], merchant_recovery_status=agent["merchant_recovery_status"],
        )


def simulated_signature(request: dict) -> str:
    # A transparent marker, NOT a cryptographic signature. Accepted only in fake mode.
    return "mock:" + request["shopper"].lower()
