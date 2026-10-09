"""Mock-only controls. No keys, wallet operations or onchain claims here."""
import hashlib
import json
import time

from pydantic import BaseModel, Field
from service.guard import Limits

SHOPPER = "0x" + "a" * 40
SHIP_TO = dict(name="Ana (simulation)", line1="Demo address", city="Singapore", postal_code="018956", country="SG", email="ana@example.invalid")
ADDRESS_HASH = "0x" + hashlib.sha256(json.dumps(SHIP_TO, sort_keys=True).encode()).hexdigest()


class DemoLimits(BaseModel):
    per_item_max_cents: int = Field(default=10000, ge=0)
    monthly_max_cents: int = Field(default=15000, ge=0)
    shops: list[str] = Field(default_factory=lambda: ["keychron.com", "twelvesouth.com", "satechi.net", "zmdesktop.com", "gymshark.com"])
    ends_at: int = 1793491200


class DemoState:
    def __init__(self):
        self.reset()

    def reset(self):
        self.limits = Limits()  # Set limits explicitly before buying.
        self.deposit = 500_000_000
        self.reserved = 0
        self.fees_paid = 0
        self.score_total = 500
        self.score_count = 5
        self.claiming: set[int] = set()

    def set_limits(self, values: DemoLimits):
        self.limits = Limits(**values.model_dump(), address_hash=ADDRESS_HASH,
                             spent_this_month_cents=self.limits.spent_this_month_cents)

    def metrics(self):
        avg = self.score_total // self.score_count
        return dict(agent_id="1", maker_deposit=self.deposit, reserved_cover=self.reserved,
                    free_cover=self.deposit - self.reserved, score_average=avg,
                    score_count=self.score_count, fee_bps=50 + 5 * (100 - avg),
                    auto_pay_limit_cents=self.limits.per_item_max_cents if avg >= 90 else (5000 if avg >= 60 else 0),
                    fees_paid=self.fees_paid)


def simulated_signature(request: dict) -> str:
    # A transparent marker, NOT a cryptographic signature. Accepted only in fake mode.
    return "mock:" + request["shopper"].lower()
