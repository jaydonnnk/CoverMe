"""One process, one small receipt store, latest 200 ledger events."""
import asyncio

from service.models import Event, Purchase, RequestDraft, AskedItem


class Store:
    def __init__(self):
        self.purchases: dict[int, Purchase] = {}
        self.events: list[Event] = []
        self.subscribers: set[asyncio.Queue] = set()
        self.counter = 0

    def add_purchase(self, request: RequestDraft, simulation: bool) -> Purchase:
        self.counter += 1
        p = Purchase(id=self.counter, agent_id=request.agentId, simulation=simulation,
                     asked=AskedItem(**request.model_dump(include={"shop", "item", "colour", "size", "model"})))
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
        # Keep IDs monotonic so an existing SSE client cannot confuse receipts.
