"""One process, one small receipt store, latest 200 ledger events."""
import asyncio

from service.models import Event, PricingSnapshot, Purchase, RequestDraft, AskedItem


class Store:
    def __init__(self):
        self.purchases: dict[int, Purchase] = {}
        self.events: list[Event] = []
        self.subscribers: set[asyncio.Queue] = set()
        self.quotes: dict[str, PricingSnapshot] = {}
        self.used_quotes: set[str] = set()
        self.counter = 0

    def save_quote(self, quote: PricingSnapshot):
        self.quotes[quote.quote_id] = quote

    def get_quote(self, quote_id: str | None) -> PricingSnapshot | None:
        return self.quotes.get(quote_id) if quote_id else None

    def reserve_quote(self, quote_id: str | None) -> PricingSnapshot | None:
        if not quote_id or quote_id in self.used_quotes:
            return None
        quote = self.quotes.get(quote_id)
        if quote:
            self.used_quotes.add(quote_id)
        return quote

    def add_purchase(self, request: RequestDraft, simulation: bool, quote: PricingSnapshot | None = None,
                     provider_name: str | None = None, agent_name: str | None = None,
                     fee_type: str | None = None, fee_value: int | None = None,
                     failure_injected: bool = False) -> Purchase:
        self.counter += 1
        p = Purchase(id=self.counter, agent_id=request.agentId, simulation=simulation,
                     asked=AskedItem(**request.model_dump(include={"shop", "item", "colour", "size", "model"})),
                     agent_listing_id=quote.agent_listing_id if quote else None,
                     provider_name=provider_name, agent_name=agent_name,
                     fee_type=fee_type, fee_value=fee_value,
                     service_fee_cents=quote.service_fee_cents if quote else 0,
                     shipping_cents=quote.shipping_cents if quote else 0,
                     tax_cents=quote.tax_cents if quote else 0,
                     buyer_total_cents=quote.buyer_total_cents if quote else None,
                     refundable_usdc=quote.refundable_usdc if quote else None,
                     failure_injected=failure_injected)
        self.purchases[p.id] = p
        return p

    def get_purchase(self, purchase_id: int) -> Purchase | None:
        return self.purchases.get(purchase_id)

    def append_event(self, event: Event):
        self.events.append(event)
        self.events = self.events[-200:]
        for queue in self.subscribers:
            queue.put_nowait(event)

    def subscribe(self):
        queue = asyncio.Queue()
        self.subscribers.add(queue)
        return queue

    def unsubscribe(self, queue):
        self.subscribers.discard(queue)

    def reset(self):
        self.purchases.clear()
        self.events.clear()
        self.quotes.clear()
        self.used_quotes.clear()
        # Keep IDs monotonic so an existing SSE client cannot confuse receipts.
