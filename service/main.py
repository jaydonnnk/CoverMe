"""FastAPI orchestration and a process-local SSE ledger."""
import asyncio
import os
import secrets
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from service.agent import chat
from service.catalogue import find_item
from service.demo import ADDRESS_HASH, SHOPPER, DemoLimits, DemoState, FailureMode, ProviderFeeUpdate
from service.models import ChatRequest, ChatResponse, Event, PricingSnapshot, SignedPurchaseRequest
from service.runner import Adapter, run_purchase
from service.store import Store

load_dotenv()


def event_key(event: Event) -> str:
    return f"{event.purchase_id}:{event.step}:{event.ts}:{event.tx_hash or ''}"


def frame(event: Event) -> str:
    return f"id: {event_key(event)}\nevent: purchase\ndata: {event.model_dump_json()}\n\n"


def create_app(mode: str | None = None):
    store, demo = Store(), DemoState()
    adapter = Adapter(mode or os.getenv("PAYMENTS_MODE", "fake"), demo)
    tasks: set[asyncio.Task] = set()

    @asynccontextmanager
    async def lifespan(app):
        yield
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    app = FastAPI(title="Cover service", version="0.2.0", lifespan=lifespan)
    app.state.store, app.state.demo, app.state.adapter = store, demo, adapter
    app.add_middleware(CORSMiddleware,
                       allow_origins=[x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",") if x.strip()],
                       allow_methods=["GET", "POST"], allow_headers=["Content-Type", "Last-Event-ID"])

    def start(coroutine):
        task = asyncio.create_task(coroutine)
        tasks.add(task)
        task.add_done_callback(tasks.discard)

    def mock_only():
        if not adapter.simulation:
            raise HTTPException(404, "Simulation controls are disabled in live mode")

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "cover", "mode": "fake" if adapter.simulation else "live"}

    @app.get("/config")
    async def config():
        return dict(mode="fake" if adapter.simulation else "live",
                    agent_mode="openai" if os.getenv("OPENAI_API_KEY") else "scripted",
                    shopper=SHOPPER if adapter.simulation else os.getenv("ANA_ADDRESS"),
                    address_hash=ADDRESS_HASH if adapter.simulation else os.getenv("ANA_ADDRESS_HASH"),
                    shipping_summary="Demo address · Singapore 018956" if adapter.simulation else "Saved Ana address (server configured)",
                     live_wallet_available=False)

    @app.get("/agents")
    async def agents():
        if adapter.simulation:
            return demo.listings()
        return []

    @app.post("/chat", response_model=ChatResponse)
    async def chat_route(body: ChatRequest):
        try:
            listing = next((item for item in demo.listings() if item.id == body.agent_listing_id), None) if adapter.simulation else None
            if adapter.simulation and listing is None:
                raise ValueError("Select an available agent before chatting")
            result = await chat(body.message, adapter.simulation, listing)
            if result.request_draft and listing:
                row = find_item(result.request_draft.item)
                if row is None:
                    raise ValueError("The selected item is not in the demo catalogue")
                if listing.fee_type == "flat":
                    service_fee = listing.fee_value
                else:
                    service_fee = (row["cents"] * listing.fee_value + 5000) // 10000
                total = row["cents"] + service_fee
                pricing = PricingSnapshot(
                    quote_id="demo_" + secrets.token_hex(8), agent_listing_id=listing.id,
                    item=result.request_draft.item, shop=result.request_draft.shop,
                    fee_type=listing.fee_type, fee_value=listing.fee_value,
                    item_subtotal_cents=row["cents"], service_fee_cents=service_fee,
                    buyer_total_cents=total, refundable_usdc=total * 10000,
                )
                store.save_quote(pricing)
                result = result.model_copy(update={"quote_id": pricing.quote_id, "pricing": pricing})
            return result
        except Exception as exc:
            raise HTTPException(502, f"Shopping agent unavailable: {exc}") from exc

    @app.post("/requests")
    async def requests(body: SignedPurchaseRequest):
        quote = store.reserve_quote(body.quote_id) if adapter.simulation else None
        if adapter.simulation and quote is None:
            raise HTTPException(409, "Pricing snapshot is missing, expired or already used")
        listing = demo.listing(quote.agent_listing_id) if quote else None
        expected_agent = listing["erc8004_agent_id"] or "2" if listing else body.request.agentId
        if listing and body.request.agentId != expected_agent:
            raise HTTPException(409, "Selected agent does not match the signed request")
        p = store.add_purchase(
            body.request, adapter.simulation, quote,
            provider_name=listing["provider_name"] if listing else None,
            agent_name=listing["agent_name"] if listing else None,
            fee_type=quote.fee_type if quote else None,
            fee_value=quote.fee_value if quote else None,
            failure_injected=demo.failure_injection if adapter.simulation else False,
        )
        start(run_purchase(p.id, body, store, adapter))
        return {"purchase_id": p.id}

    @app.get("/purchases/{purchase_id}")
    async def purchase(purchase_id: int):
        p = store.get_purchase(purchase_id)
        if p is None:
            raise HTTPException(404, "Purchase not found")
        return p

    @app.get("/events")
    async def events(request: Request):
        async def stream():
            queue = store.subscribe()
            history = list(store.events)
            last_id = request.headers.get("last-event-id")
            if last_id:
                match = next((i for i, e in enumerate(history) if event_key(e) == last_id), None)
                if match is not None:
                    history = history[match + 1:]
            try:
                yield ": connected\n\n"
                for event in history:
                    yield frame(event)
                while not await request.is_disconnected():
                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=15)
                        yield frame(event)
                    except asyncio.TimeoutError:
                        yield ": heartbeat\n\n"
            finally:
                store.unsubscribe(queue)
        return StreamingResponse(stream(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @app.post("/demo/limits")
    async def limits(values: DemoLimits):
        mock_only()
        demo.set_limits(values)
        return {"status": "confirmed", "simulation": True}

    @app.get("/demo/maker")
    async def maker(agent_listing_id: str = "atlas"):
        mock_only()
        try:
            return demo.metrics(agent_listing_id)
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.post("/demo/providers/{agent_listing_id}")
    async def provider_fee(agent_listing_id: str, values: ProviderFeeUpdate):
        mock_only()
        try:
            demo.set_fee(agent_listing_id, values)
            return demo.metrics(agent_listing_id)
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.post("/demo/failure-mode")
    async def failure_mode(values: FailureMode):
        mock_only()
        demo.failure_injection = values.enabled
        return {"enabled": demo.failure_injection, "simulation": True}

    async def claim(p):
        try:
            p.status = "claimed"
            store.append_event(Event(purchase_id=p.id, step="claimed", detail="Simulated wrong-item claim opened"))
            await asyncio.sleep(0.6)
            mismatch = any(getattr(p.asked, field) and getattr(p.asked, field) != getattr(p.bought, field)
                           for field in ("colour", "size", "model", "shop"))
            p.status = "refunded" if mismatch else "rejected"
            tx = f"0xmock_{p.id}_{p.status}"
            p.tx_hash = tx
            agent = demo.listing(p.agent_listing_id or "atlas")
            refund = p.refundable_usdc or p.charge_usdc
            agent["reserved"] -= refund
            if mismatch:
                agent["deposit"] -= refund
                agent["provider_loss"] += refund
                agent["service_earnings"] = max(0, agent["service_earnings"] - p.service_fee_cents * 10000)
                agent["merchant_recovery_status"] = "pending"
                p.refund_amount_usdc = refund
                p.merchant_recovery_status = "pending"
                p.refund_tx_hash = tx
            agent["score_total"] += 0 if mismatch else 100
            agent["score_count"] += 1
            store.append_event(Event(purchase_id=p.id, step=p.status, tx_hash=tx,
                                     detail="Simulated full approved-total refund from provider deposit" if mismatch else "Simulated claim rejected: attributes match"))
            store.append_event(Event(purchase_id=p.id, step="score_written", detail=f"Simulated score updated to {demo.metrics(p.agent_listing_id or 'atlas')['score_average']}"))
        finally:
            demo.claiming.discard(p.id)

    @app.post("/demo/claims/{purchase_id}")
    async def claim_route(purchase_id: int):
        mock_only()
        p = store.get_purchase(purchase_id)
        if not p:
            raise HTTPException(404, "Purchase not found")
        if p.status != "confirmed" or p.id in demo.claiming:
            raise HTTPException(409, "Only a confirmed purchase can be claimed once")
        demo.claiming.add(p.id)
        start(claim(p))
        return {"status": "waiting", "simulation": True}

    @app.post("/demo/reset")
    async def reset():
        mock_only()
        if tasks:
            raise HTTPException(409, "Wait for the current purchase or claim to finish")
        store.reset()
        demo.reset()
        return {"status": "reset", "simulation": True}

    return app


app = create_app()
