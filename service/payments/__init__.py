"""Cover's payments (3.1). `kwal` wraps the Kwal skill; `flow.pay()` runs a
covered purchase against a `flow.Checkpoint` (web3.py in `chain.py`, J7).
Importing this package never touches the network or the Kwal skill; the
first Kwal call does."""
from .flow import Event, NeedsApproval, PaymentFailed, Released, bought, pay, pay_approved, use_chain
from .kwal import (
    KwalError,
    Product,
    Quote,
    QuoteNotPayable,
    ShipTo,
    checkout,
    funding,
    options,
    payment,
    quote,
    read_quote,
    search,
    use_replay,
    variant,
    wait_for_funding,
    wait_for_payment,
)



def check(request: dict, signature: str, q: Quote) -> list[str]:
    """3.1: `Checkpoint.check()` for this quote; every failed rule by name
    ([] = release will pass). `["needs_approval"]` alone means A5, not a refusal."""
    from service.guard.rules import from_bitmask

    from . import flow
    from .chain import default

    chain = flow._chain or default()
    return from_bitmask(chain.check(request, signature, bought(q)))


__all__ = [
    "Event",
    "KwalError",
    "NeedsApproval",
    "PaymentFailed",
    "Product",
    "Quote",
    "QuoteNotPayable",
    "Released",
    "ShipTo",
    "bought",
    "check",
    "checkout",
    "funding",
    "options",
    "pay",
    "pay_approved",
    "payment",
    "quote",
    "read_quote",
    "search",
    "use_chain",
    "use_replay",
    "variant",
    "wait_for_funding",
    "wait_for_payment",
]
