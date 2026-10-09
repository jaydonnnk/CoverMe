"""FastAPI orchestration and a process-local SSE ledger."""
import asyncio
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from service.agent import chat
from service.demo import ADDRESS_HASH, SHOPPER, DemoLimits, DemoState
from service.models import ChatRequest, ChatResponse, Event, SignedPurchaseRequest
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

    @app.post("/chat", response_model=ChatResponse)
    async def chat_route(body: ChatRequest):
        try:
            return await chat(body.message, adapter.simulation)
        except Exception as exc:
            raise HTTPException(502, f"Shopping agent unavailable: {exc}") from exc

    @app.post("/requests")
    async def requests(body: SignedPurchaseRequest):
        p = store.add_purchase(body.request, adapter.simulation)
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
    async def maker():
        mock_only()
        return demo.metrics()

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
            demo.reserved -= p.charge_usdc
            if mismatch:
                demo.deposit -= p.charge_usdc
                p.refund_tx_hash = tx
            demo.score_total += 0 if mismatch else 100
            demo.score_count += 1
            store.append_event(Event(purchase_id=p.id, step=p.status, tx_hash=tx,
                                     detail="Simulated refund from maker deposit" if mismatch else "Simulated claim rejected: attributes match"))
            store.append_event(Event(purchase_id=p.id, step="score_written", detail=f"Simulated score updated to {demo.metrics()['score_average']}"))
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
