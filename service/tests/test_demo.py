import asyncio
import time

import pytest
from fastapi.testclient import TestClient

from service import fake_payments
from service.agent import chat
from service.demo import DemoLimits, DemoState, simulated_signature
from service.main import create_app, frame
from service.models import Event, SignedPurchaseRequest
from service.runner import Adapter, run_purchase
from service.store import Store


@pytest.fixture(autouse=True)
def no_openai(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(fake_payments, "STEP_DELAY", 0)


@pytest.mark.parametrize("prompt,shop,colour,maximum", [
    ("Get me the Keychron B40", "keychron.com", "deep black", 10000),
    ("Buy the black PowerBug 25W, under $60", "twelvesouth.com", "black", 6000),
])
def test_chat_draft(prompt, shop, colour, maximum):
    result = asyncio.run(chat(prompt, True))
    assert result.mode == "scripted"
    assert result.request_draft.shop == shop
    assert result.request_draft.colour == colour
    assert result.request_draft.maxUsdCents == maximum


def test_non_purchase_chat():
    assert asyncio.run(chat("Hello", True)).request_draft is None


def test_store_broadcast_and_retention():
    store = Store()
    a, b = store.subscribe(), store.subscribe()
    for i in range(205):
        store.append_event(Event(purchase_id=i, step="checked", detail="ok"))
    assert len(store.events) == 200
    assert a.get_nowait() == b.get_nowait()
    store.unsubscribe(a)
    assert a not in store.subscribers
    assert "event: purchase\ndata: " in frame(store.events[-1])


def test_runner_success_refusal_and_lookup():
    async def check():
        store, demo = Store(), DemoState()
        demo.set_limits(DemoLimits())
        adapter = Adapter("fake", demo)
        for prompt in ("Get me the Keychron B40", "Show me today's deal", "Buy the black PowerBug 25W, under $60"):
            draft = (await chat(prompt, True)).request_draft
            p = store.add_purchase(draft, True)
            await run_purchase(p.id, SignedPurchaseRequest(request=draft, signature=simulated_signature(draft.model_dump())), store, adapter)
            events = [e for e in store.events if e.purchase_id == p.id]
            if "deal" in prompt:
                assert [e.step for e in events] == ["refused"]
                assert p.failures == ["over_request_max", "shop_not_allowed", "wrong_address"]
                assert "No money moved" in events[0].detail
            else:
                assert [e.step for e in events] == ["checked", "released", "fee_taken", "funded", "paid", "confirmed"]
                assert store.get_purchase(p.id).kwal_payment_id.startswith("kwal_mock_")
                assert p.bought.colour == ("white/dune" if "PowerBug" in prompt else "deep black")
    asyncio.run(check())


def wait_for(client, purchase_id, status):
    for _ in range(100):
        p = client.get(f"/purchases/{purchase_id}").json()
        if p["status"] == status:
            return p
        time.sleep(0.02)
    raise AssertionError(p)


def test_http_sequence_twice():
    with TestClient(create_app("fake")) as client:
        for _ in range(2):
            assert client.post("/demo/reset").status_code == 200
            assert client.post("/demo/limits", json=DemoLimits().model_dump()).status_code == 200
            for prompt, expected in (("Get me the Keychron B40", "confirmed"), ("Show me today's deal", "refused"), ("Buy the black PowerBug 25W, under $60", "confirmed")):
                response = client.post("/chat", json={"message": prompt})
                assert response.status_code == 200
                draft = response.json()["request_draft"]
                response = client.post("/requests", json={"request": draft, "signature": simulated_signature(draft)})
                assert response.status_code == 200
                purchase_id = response.json()["purchase_id"]
                p = wait_for(client, purchase_id, expected)
                assert p["asked"] and p["bought"]
            assert client.post(f"/demo/claims/{purchase_id}").status_code == 200
            p = wait_for(client, purchase_id, "refunded")
            assert p["refund_tx_hash"].startswith("0xmock_")
            assert client.get("/demo/maker").json()["score_average"] == 83
        assert client.get("/purchases/99999").status_code == 404


def test_bad_simulation_signature_moves_nothing():
    async def check():
        store, demo = Store(), DemoState()
        draft = (await chat("Get me the Keychron B40", True)).request_draft
        p = store.add_purchase(draft, True)
        await run_purchase(p.id, SignedPurchaseRequest(request=draft, signature="bad"), store, Adapter("fake", demo))
        assert p.status == "error"
        assert demo.reserved == 0
        assert store.events[0].status == "error"
    asyncio.run(check())


def test_live_does_not_fall_back_to_simulation():
    with pytest.raises((ModuleNotFoundError, RuntimeError)):
        create_app("live")
