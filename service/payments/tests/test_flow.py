"""pay() on fakes: no chain, no Kwal, no network."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from service.guard.rules import to_bitmask
from service.payments import flow
from service.payments.flow import FAILED, PAID, NeedsApproval, PaymentFailed, Released, bought, pay, payment_id_hash
from service.payments.kwal import Quote, QuoteNotPayable

RID = "0x" + "11" * 32


def sisu(**overrides) -> Quote:
    base = dict(
        quote_id="1d809e2a-6e71-4321-8b1f-fb75d74c43e2",
        product_id="prd_1",
        variant_id="var_1",
        shop="forza sports",
        title="SISU Large Aero Guard 2.0mm",
        colour="snow white",
        size="",
        model="",
        image_url=None,
        listed_usd_cents=1_999,
        charge_usdc=21_710_000,
        sandbox_pricing=False,
    )
    base.update(overrides)
    return Quote(**base)


class FakeChain:
    def __init__(self, mask: int = 0):
        self.mask = mask
        self.calls: list[tuple] = []

    def request_id(self, request):
        return RID

    def check(self, request, signature, b):
        self.calls.append(("check", b))
        return self.mask

    def release(self, request, signature, b):
        self.calls.append(("release", b))
        return Released(purchase_id=7, tx_hash="0xrelease", fee_usdc=108_550)

    def confirm(self, purchase_id, pid_hash, status):
        self.calls.append(("confirm", purchase_id, pid_hash, status))
        return "0xconfirm"


class FakeKwal:
    def __init__(self, funding="ready", payment="completed", checkout_error=None):
        self.funding, self.payment, self.checkout_error = funding, payment, checkout_error
        self.calls: list[tuple] = []

    def wait_for_funding(self, quote_id, timeout):
        self.calls.append(("funding", quote_id, timeout))
        return SimpleNamespace(state=self.funding)

    def checkout(self, quote_id):
        self.calls.append(("checkout", quote_id))
        if self.checkout_error:
            raise self.checkout_error
        return SimpleNamespace(payment_id="pay_de230427", state="pending")

    def wait_for_payment(self, payment_id, timeout, *, quote_id=None):
        self.calls.append(("payment", payment_id, quote_id))
        return SimpleNamespace(state=self.payment, reason="card declined", approval_url=None)


def run(chain, kwal, q=None):
    """Collect events; return (events, exception or None)."""

    async def go():
        events = []
        try:
            async for e in pay({"nonce": 1}, "0xsig", q or sisu(), chain=chain, kwal=kwal):
                events.append(e)
        except Exception as exc:  # noqa: BLE001
            return events, exc
        return events, None

    return asyncio.run(go())


def steps(events):
    return [(e.step, e.status) for e in events]


def test_happy_path_emits_every_step_and_confirms_paid():
    chain, kwal = FakeChain(), FakeKwal()
    events, exc = run(chain, kwal)
    assert exc is None
    assert steps(events) == [
        ("checked", "ok"),
        ("released", "ok"),
        ("fee_taken", "ok"),
        ("funded", "waiting"),
        ("funded", "ok"),
        ("paid", "waiting"),
        ("paid", "ok"),
        ("confirmed", "ok"),
    ]
    assert all(e.request_id == RID for e in events)
    assert events[0].purchase_id is None and all(e.purchase_id == 7 for e in events[1:])
    assert events[1].tx_hash == "0xrelease" and events[-1].tx_hash == "0xconfirm"
    assert events[-1].kwal_payment_id == "pay_de230427"
    assert "0.11 USDC" in events[2].detail
    assert chain.calls[-1] == ("confirm", 7, payment_id_hash("pay_de230427"), PAID)
    assert [c[0] for c in kwal.calls] == ["funding", "checkout", "payment"]
    assert kwal.calls[0][2] == flow.FUNDING_TIMEOUT >= 60  # J4: ~38 s to see a contract transfer


def test_refused_reports_every_rule_and_moves_nothing():
    chain, kwal = FakeChain(to_bitmask(["over_request_max", "shop_not_allowed", "wrong_address"])), FakeKwal()
    events, exc = run(chain, kwal)
    assert exc is None
    assert steps(events) == [("refused", "error")]
    assert events[0].detail == "Refused: amount, shop, address"
    assert [c[0] for c in chain.calls] == ["check"]
    assert kwal.calls == []


def test_needs_approval_alone_parks_and_raises():
    chain, kwal = FakeChain(to_bitmask(["needs_approval"])), FakeKwal()
    events, exc = run(chain, kwal)
    assert steps(events) == [("needs_approval", "waiting")]
    assert isinstance(exc, NeedsApproval) and exc.request_id == RID
    assert [c[0] for c in chain.calls] == ["check"]


def test_needs_approval_with_a_broken_limit_is_refused():
    """Ana's approval can't lift her own limits, so this is a plain refusal."""
    chain = FakeChain(to_bitmask(["over_per_item", "needs_approval"]))
    events, exc = run(chain, FakeKwal())
    assert exc is None
    assert events[0].step == "refused"
    assert events[0].detail == "Refused: item cap, needs your OK"


def test_funding_never_ready_confirms_failed_and_skips_checkout():
    chain, kwal = FakeChain(), FakeKwal(funding="processing")
    events, exc = run(chain, kwal)
    assert isinstance(exc, PaymentFailed) and exc.confirmed and exc.purchase_id == 7
    assert steps(events)[-1] == ("funded", "error")
    assert "processing" in events[-1].detail
    assert chain.calls[-1] == ("confirm", 7, payment_id_hash(""), FAILED)
    assert "checkout" not in [c[0] for c in kwal.calls]


def test_expired_quote_at_checkout_confirms_failed():
    chain, kwal = FakeChain(), FakeKwal(checkout_error=QuoteNotPayable("Quote q expired"))
    events, exc = run(chain, kwal)
    assert isinstance(exc, PaymentFailed) and exc.confirmed
    assert steps(events)[-1] == ("paid", "error")
    assert chain.calls[-1][3] == FAILED


def test_declined_payment_confirms_failed():
    chain, kwal = FakeChain(), FakeKwal(payment="declined")
    events, exc = run(chain, kwal)
    assert isinstance(exc, PaymentFailed) and exc.confirmed
    assert events[-1].detail == "Payment declined: card declined"
    assert chain.calls[-1] == ("confirm", 7, payment_id_hash("pay_de230427"), FAILED)


def test_unfinished_payment_is_not_confirmed():
    """Still pending (or an approval link) at the timeout: the outcome is unknown."""
    chain, kwal = FakeChain(), FakeKwal(payment="pending")
    events, exc = run(chain, kwal)
    assert isinstance(exc, PaymentFailed) and not exc.confirmed
    assert steps(events)[-1] == ("paid", "error")
    assert "confirm" not in [c[0] for c in chain.calls]


def test_bought_maps_the_quote_to_the_solidity_struct():
    b = bought(sisu())
    assert b["shop"] == "forza sports" and b["colour"] == "snow white"
    assert b["listedUsdCents"] == 1_999 and b["chargeUsdc"] == 21_710_000
    assert b["quoteIdHash"].startswith("0x") and len(b["quoteIdHash"]) == 66


def test_one_payment_at_a_time():
    order: list[str] = []

    class SlowKwal(FakeKwal):
        def wait_for_funding(self, quote_id, timeout):
            order.append(f"fund {quote_id}")
            return super().wait_for_funding(quote_id, timeout)

    class LoggingChain(FakeChain):
        def confirm(self, purchase_id, pid_hash, status):
            order.append("confirm")
            return super().confirm(purchase_id, pid_hash, status)

    async def one(qid):
        async for _ in pay({}, "0x", sisu(quote_id=qid), chain=LoggingChain(), kwal=SlowKwal()):
            await asyncio.sleep(0)  # give the other payment every chance to interleave

    async def both():
        await asyncio.gather(one("a"), one("b"))

    asyncio.run(both())
    assert order == ["fund a", "confirm", "fund b", "confirm"]


def test_no_chain_configured_raises():
    flow.use_chain(None)
    events, exc = run(None, FakeKwal())
    assert events == [] and isinstance(exc, RuntimeError)


def test_event_shape_matches_3_5():
    events, _ = run(FakeChain(), FakeKwal())
    d = events[-1].to_dict()
    assert set(d) == {"purchase_id", "step", "status", "tx_hash", "kwal_payment_id", "detail", "ts", "request_id"}
    assert d["ts"].endswith("Z")
