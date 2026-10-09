"""Explicit simulation of the shared payment interface; never sends money."""
import asyncio
from dataclasses import dataclass

from service.catalogue import CATALOGUE
from service.models import Event

STEP_DELAY = 0.15


@dataclass
class ShipTo:
    name: str
    line1: str
    city: str
    postal_code: str
    country: str
    email: str


@dataclass
class Quote:
    quote_id: str
    product_id: str
    variant_id: str
    shop: str
    title: str
    colour: str
    size: str
    model: str
    image_url: str | None
    listed_usd_cents: int
    charge_usdc: int
    sandbox_pricing: bool


def quote(variant_id: str, quantity: int, ship_to: ShipTo) -> Quote:
    if quantity != 1:
        raise ValueError("The MVP supports one item per signed request")
    row = next(v for v in CATALOGUE.values() if v["variant_id"] == variant_id)
    return Quote(f"mock_quote_{variant_id}", variant_id, variant_id, row["shop"], row["item"],
                 row["colour"], "", "", None, row["cents"], row["cents"] * 10000, False)


def check(request: dict, signature: str, q: Quote) -> list[str]:
    return []  # Rules/ceiling are still checked by Jaydon's real guard.


async def pay(request: dict, signature: str, q: Quote):
    # Temporary ID is assigned by runner; live correlation remains a Jaydon handoff.
    for step, detail in (
        ("released", "Simulated release; cover reserved"),
        ("fee_taken", "Simulated cover fee recorded"),
        ("funded", "Simulated vault funding"),
        ("paid", "Simulated merchant payment"),
        ("confirmed", "Simulated purchase confirmed"),
    ):
        await asyncio.sleep(STEP_DELAY)
        yield Event(purchase_id=0, step=step, detail=detail,
                    tx_hash=f"0xmock_{request['nonce']}_{step}",
                    kwal_payment_id=f"kwal_mock_{request['nonce']}" if step in ("paid", "confirmed") else None)
