"""Builders for the guard tests: no network, no chain, no Kwal."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from service.guard.rules import Limits

NOW = 1_791_600_000  # fixed clock for every test
SHOP = "twelvesouth.com"
ADDRESS_HASH = "0x" + "ab" * 32
ANA = "0x3aDe6336e45c37a41193aEcb9b02315eA59268d0"


@dataclass
class FakeQuote:  # the 3.1 Quote fields
    listed_usd_cents: int
    charge_usdc: int
    shop: str = SHOP
    quote_id: str = "q-1"
    product_id: str = "prod_1"
    variant_id: str = "var_1"
    title: str = "PowerBug 25W"
    colour: str = "white/dune"
    size: str = ""
    model: str = ""
    image_url: Optional[str] = None
    sandbox_pricing: bool = False


def quote(cents: int, *, charge_usdc: Optional[int] = None, shop: str = SHOP) -> FakeQuote:
    """A quote whose listed price and charge are the same amount by default."""
    return FakeQuote(
        listed_usd_cents=cents,
        charge_usdc=cents * 10_000 if charge_usdc is None else charge_usdc,
        shop=shop,
    )


def limits(**overrides) -> Limits:
    """laeria's `full()`: fully specified, permissive but bounded."""
    base = dict(
        per_item_max_cents=10_000,
        monthly_max_cents=50_000,
        shops=[SHOP],
        address_hash=ADDRESS_HASH,
        ends_at=NOW + 86_400,
        spent_this_month_cents=0,
    )
    base.update(overrides)
    return Limits(**base)


def request(**overrides) -> dict:
    base = dict(
        shopper=ANA,
        agentId=1,
        shop=SHOP,
        item="powerbug 25w",
        colour="slate/black",
        size="",
        model="",
        maxUsdCents=1_000_000,
        addressHash=ADDRESS_HASH,
        nonce=1,
        deadline=NOW + 600,
    )
    base.update(overrides)
    return base
