"""One signed-request pipeline. Adapters selected once, not inside payment steps."""
import asyncio
import importlib
import json
import os
from dataclasses import asdict, is_dataclass
from pathlib import Path

from service import fake_payments, guard
from service.catalogue import find_item
from service.demo import DemoState, SHIP_TO, simulated_signature
from service.models import BoughtItem, Event, SignedPurchaseRequest
from service.store import Store


class Adapter:
    def __init__(self, mode: str, demo: DemoState):
        if mode not in ("fake", "live"):
            raise ValueError("PAYMENTS_MODE must be fake or live")
        self.demo = demo
        self.simulation = mode == "fake"
        self.payments = fake_payments if self.simulation else importlib.import_module("service.payments")
        if not self.simulation:
            self.chain = importlib.import_module("service.payments.chain")
            for name in ("quote", "check", "pay", "ShipTo"):
                if not hasattr(self.payments, name):
                    raise RuntimeError(f"Live payment interface missing: {name}")
            # These two chain getters still require Jaydon's F2 agreement.
            for name in ("get_limits", "get_free_cover"):
                if not hasattr(self.chain, name):
                    raise RuntimeError(f"Live chain integration missing: {name}")
            deployments = json.loads((Path(__file__).resolve().parents[1] / "deployments/ink-sepolia.json").read_text())
            for section in ("registries", "cover"):
                for name, value in deployments[section].items():
                    if name != "agentId" and (not value["address"] or not value["abi"]):
                        raise RuntimeError(f"Live deployment missing: {name}")
            for name in ("ANA_SHIP_TO_JSON", "ANA_ADDRESS", "ANA_ADDRESS_HASH", "OPENAI_API_KEY"):
                if not os.getenv(name):
                    raise RuntimeError(f"Live configuration missing: {name}")

    def verify(self, request: dict, signature: str):
        if self.simulation:
            if signature != simulated_signature(request):
                raise ValueError("Invalid simulated signature marker")
            return request["shopper"]
        return guard.verify_request(request, signature)

    def shipping(self):
        # In live mode shipping comes only from the saved server environment.
        saved = SHIP_TO if self.simulation else json.loads(os.environ["ANA_SHIP_TO_JSON"])
        return self.payments.ShipTo(**saved)

    def limits(self, shopper):
        return self.demo.limits if self.simulation else self.chain.get_limits(shopper)

    def free_cover(self, agent_id, listing_id=None):
        return self.demo.metrics(listing_id or "atlas")["free_cover"] if self.simulation else self.chain.get_free_cover(agent_id)


async def run_purchase(purchase_id: int, signed: SignedPurchaseRequest, store: Store, adapter: Adapter):
    purchase = store.get_purchase(purchase_id)
    request = signed.request.model_dump()
    try:
        snapshot = store.get_quote(signed.quote_id)
        if adapter.simulation:
            if snapshot is None:
                raise ValueError("Missing or expired pricing snapshot")
            if snapshot.agent_listing_id != purchase.agent_listing_id:
                raise ValueError("Selected agent does not match the approved quote")
            if snapshot.item != request["item"] or snapshot.shop != request["shop"]:
                raise ValueError("Purchase request does not match the approved quote")
        await asyncio.to_thread(adapter.verify, request, signed.signature)
        row = find_item(request["item"])
        if row is None:
            raise ValueError("No demo catalogue product matches this request")
        q = await asyncio.to_thread(adapter.payments.quote, row["variant_id"], 1, adapter.shipping())
        if snapshot and (snapshot.item_subtotal_cents != q.listed_usd_cents or snapshot.shop != q.shop):
            raise ValueError("Catalogue price or merchant changed after approval")
        limits = await asyncio.to_thread(adapter.limits, request["shopper"])
        free_cover = await asyncio.to_thread(adapter.free_cover, request["agentId"], purchase.agent_listing_id)
        failures = guard.check_rules(request, q, limits)
        ceiling = guard.spend_ceiling_cents(request, q, limits, free_cover)
        refundable = purchase.refundable_usdc or q.charge_usdc
        fee_bps = adapter.demo.metrics(purchase.agent_listing_id or "atlas")["fee_bps"] if adapter.simulation else 0
        cover_fee = q.charge_usdc * fee_bps // 10000
        if refundable + cover_fee > free_cover and "not_enough_cover" not in failures:
            failures.append("not_enough_cover")
        if not failures and guard.purchase_cents(q) > ceiling:
            failures.append("not_enough_cover")
        failures += await asyncio.to_thread(adapter.payments.check, request, signed.signature, q)
        mismatch = any(request[field] and request[field] != getattr(q, field) for field in ("colour", "size", "model"))
        if mismatch and not purchase.failure_injected:
            failures.append("variant_mismatch")
        if adapter.simulation and q.shop == "gmktec.com":
            # The presentation beat groups all amount caps into one stable amount
            # reason and deliberately demonstrates exactly amount/shop/address.
            failures = [name for name in ("over_request_max", "shop_not_allowed", "wrong_address") if name in failures]
        purchase.bought = BoughtItem(shop=q.shop, item=q.title, colour=q.colour, size=q.size, model=q.model, image_url=q.image_url)
        purchase.listed_usd_cents, purchase.charge_usdc = q.listed_usd_cents, q.charge_usdc
        purchase.sandbox_pricing = q.sandbox_pricing
        if failures:
            purchase.status = "refused"
            purchase.failures = list(dict.fromkeys(failures))
            store.append_event(Event(purchase_id=purchase_id, step="refused", status="error",
                                     detail="Refused: " + ", ".join(purchase.failures) + ". No money moved."))
            return
        store.append_event(Event(purchase_id=purchase_id, step="checked", detail="Request passed all limits"))
        async for raw in adapter.payments.pay(request, signed.signature, q):
            data = raw.model_dump() if hasattr(raw, "model_dump") else (asdict(raw) if is_dataclass(raw) else dict(raw))
            event = Event.model_validate(data)
            if not adapter.simulation and event.step == "released":
                purchase.onchain_purchase_id = event.purchase_id
            event.purchase_id = purchase_id
            purchase.status = event.step
            if event.tx_hash:
                purchase.tx_hash = event.tx_hash
            if event.kwal_payment_id:
                purchase.kwal_payment_id = event.kwal_payment_id
            if adapter.simulation and event.step == "released":
                agent = adapter.demo.listing(purchase.agent_listing_id or "atlas")
                agent["deposit"] -= cover_fee
                agent["fees_paid"] += cover_fee
                agent["reserved"] += refundable
            if adapter.simulation and event.step == "confirmed":
                adapter.demo.limits.spent_this_month_cents += q.listed_usd_cents
                adapter.demo.listing(purchase.agent_listing_id or "atlas")["service_earnings"] += purchase.service_fee_cents * 10000
            store.append_event(event)
    except Exception as exc:
        purchase.status = "error"
        # 'error' is a status, not a permitted shared step.
        store.append_event(Event(purchase_id=purchase_id, step="needs_review", status="error", detail=str(exc)))
