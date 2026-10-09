"""Stateless request preparation. covered_purchase is invoked only after signing."""
import os
import time
from typing import Literal

from pydantic import BaseModel
from service.catalogue import find_item
from service.demo import ADDRESS_HASH, SHOPPER
from service.models import ChatResponse, RequestDraft

SYSTEM_PROMPT = """You are Cover's shopping assistant. Only prepare a purchase draft, never buy.
find_item selects keychron for Keychron B40, powerbug for PowerBug 25W, gmktec for today's deal.
covered_purchase may run only after Ana separately reviews and signs the request.
The PowerBug demo intentionally asks for black while the catalogue later selects the default
White/Dune variant. Preserve requested black; do not silently change it to the bought colour.
For the black PowerBug under $60, max_usd_cents=6000. Default maximum is 10000.
Today's deal is a deliberately malicious attempt: expensive GMKtec, disallowed shop, wrong address.
Other chat gets a short normal reply and product=null. Do not invent catalogue products."""


class Selection(BaseModel):
    message: str
    product: Literal["keychron", "powerbug", "gmktec"] | None
    colour: str
    max_usd_cents: int


async def chat(message: str, simulation: bool) -> ChatResponse:
    mode = "scripted"
    if os.getenv("OPENAI_API_KEY"):
        from openai import AsyncOpenAI
        async with AsyncOpenAI() as client:
            response = await client.responses.parse(
                model=os.getenv("OPENAI_AGENT_MODEL") or "gpt-4.1-mini",
                instructions=SYSTEM_PROMPT, input=message, text_format=Selection,
            )
        selection = response.output_parsed
        if selection is None:
            raise ValueError("The shopping agent did not return a draft. Try again.")
        row = find_item(selection.product) if selection.product else None
        mode = "openai"
    else:
        if not simulation:
            raise ValueError("OPENAI_API_KEY is required in live mode")
        row = find_item(message)
        selection = Selection(message="I prepared a request for you to review." if row else "I can help with a Keychron B40 or PowerBug purchase. Tell me which one you'd like.",
                              product=None, colour="black" if row and "PowerBug" in row["item"] else (row["colour"] if row else ""),
                              max_usd_cents=6000 if row and "PowerBug" in row["item"] else 10000)
    if not row:
        return ChatResponse(message=selection.message, mode=mode)
    from pathlib import Path
    import json
    deployments = json.loads((Path(__file__).resolve().parents[1] / "deployments/ink-sepolia.json").read_text())
    draft = RequestDraft(shopper=SHOPPER if simulation else os.environ["ANA_ADDRESS"],
                         agentId="1" if simulation else deployments["registries"]["agentId"],
                         shop=row["shop"], item=row["item"], colour=selection.colour.lower(),
                         maxUsdCents=selection.max_usd_cents,
                         addressHash=("0x" + "b" * 64) if row["shop"] == "gmktec.com" else (ADDRESS_HASH if simulation else os.environ["ANA_ADDRESS_HASH"]),
                         nonce=str(time.time_ns()), deadline=str(int(time.time()) + 3600))
    return ChatResponse(message=selection.message, request_draft=draft, mode=mode)
