"""`pay()` (3.1, J7): release -> vault funding -> Kwal checkout -> payment -> confirm.

The chain calls sit behind `Checkpoint`, a small protocol. `chain.py` (J7)
implements it with web3.py against the deployed contracts; the tests use a
fake. Kwal calls go through `kwal.py` (or a stand-in with the same functions).

Events follow 3.5. Each also carries `request_id`, the request's EIP-712
digest (J1 item 6), because `checked`, `refused` and `needs_approval` happen
before `release` gives the purchase an id.

What the J3/J4 measurements fixed here:
- A contract transfer counts as vault funding, but Kwal takes ~38 s to see it
  and says `processing` meanwhile. So funding is awaited (90 s by default)
  and anything short of `ready` before the deadline is "still waiting".
- The first real payment completed 23 s after submit with no approval link,
  so the payment is polled to the end without a human step.

One payment at a time: `_payment_lock()` serialises `pay()` within the process,
on top of `kwal.LOCK`, which serialises single Kwal calls.
"""
from __future__ import annotations

import asyncio
import datetime as _dt
import weakref
from dataclasses import asdict, dataclass, field
from types import ModuleType
from typing import Any, AsyncIterator, Optional, Protocol

from service.guard.rules import WORDS, from_bitmask

from . import kwal as _kwal
from .kwal import Quote, QuoteNotPayable

PAID = 1  # Checkpoint.confirm status
FAILED = 2
FUNDING_TIMEOUT = 90.0  # seconds; J4 measured ~38 s for a contract transfer
PAYMENT_TIMEOUT = 300.0  # seconds; the HMX payment took 23 s

_locks: "weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Lock]" = weakref.WeakKeyDictionary()


def _payment_lock() -> asyncio.Lock:
    """One payment at a time (per event loop, so tests with fresh loops stay independent)."""
    loop = asyncio.get_running_loop()
    if loop not in _locks:
        _locks[loop] = asyncio.Lock()
    return _locks[loop]


# ------------------------------------------------------------------ types


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


@dataclass
class Event:
    """One ledger line (3.5)."""

    purchase_id: int  # the Checkpoint's id; 0 until release (models.Event needs an int)
    step: str  # checked | refused | needs_approval | released | fee_taken | funded | paid | confirmed
    status: str  # ok | waiting | error
    tx_hash: Optional[str] = None
    kwal_payment_id: Optional[str] = None
    detail: str = ""
    ts: str = field(default_factory=_now)
    request_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Released:
    purchase_id: int
    tx_hash: str
    fee_usdc: int  # from the Bond's `Reserved` event; 0 for an uncovered purchase


class Checkpoint(Protocol):
    """The chain calls `pay()` needs. `chain.py` implements these with web3.py."""

    def request_id(self, request: dict) -> str:
        """`Checkpoint.hashRequest(r)`, i.e. `guard.request_digest`."""

    def check(self, request: dict, signature: str, bought: dict) -> int:
        """`Checkpoint.check()`: the failed-rule bitmask, 0 = release will pass."""

    def release(self, request: dict, signature: str, bought: dict) -> Released:
        """`Checkpoint.release()` from the service key; waits for the receipt."""

    def confirm(self, purchase_id: int, payment_id_hash: str, status: int) -> str:
        """`Checkpoint.confirm()`; returns the tx hash."""


class NeedsApproval(Exception):
    """The agent's score band doesn't cover this amount; Ana must approve it (A5)."""

    def __init__(self, request_id: str):
        super().__init__(f"request {request_id} needs Ana's approval")
        self.request_id = request_id


class PaymentFailed(Exception):
    """Released but not paid. `confirm(FAILED)` was sent when the outcome is known."""

    def __init__(self, message: str, purchase_id: Optional[int] = None, confirmed: bool = False):
        super().__init__(message)
        self.purchase_id = purchase_id
        self.confirmed = confirmed


# --------------------------------------------------------------- helpers


def bought(q: Quote) -> dict:
    """The 3.6 `Bought` struct for a quote (field names as in Checkpoint.sol)."""
    from eth_utils import keccak

    return {
        "quoteIdHash": "0x" + keccak(text=q.quote_id).hex(),
        "shop": q.shop,
        "colour": q.colour,
        "size": q.size,
        "model": q.model,
        "listedUsdCents": int(q.listed_usd_cents),
        "chargeUsdc": int(q.charge_usdc),
    }


def payment_id_hash(payment_id: str) -> str:
    from eth_utils import keccak

    return "0x" + keccak(text=payment_id).hex()


def refusal_detail(names: list[str]) -> str:
    return "Refused: " + ", ".join(WORDS.get(n, n) for n in names)


def _usdc(units: int) -> str:
    return f"{units / 1_000_000:.2f} USDC"


_chain: Optional[Checkpoint] = None


def use_chain(chain: Optional[Checkpoint]) -> None:
    """Set the default Checkpoint for `pay()` (chain.py does this once deployed)."""
    global _chain
    _chain = chain


def _resolve_chain(chain: Optional[Checkpoint]) -> Checkpoint:
    """The given chain, else use_chain()'s, else chain.default() from the env."""
    if chain is not None:
        return chain
    if _chain is not None:
        return _chain
    from . import chain as chain_module  # web3 loads only when a payment runs

    return chain_module.default()


# -------------------------------------------------------------------- pay


async def pay(
    request: dict,
    signature: str,
    q: Quote,
    *,
    chain: Optional[Checkpoint] = None,
    kwal: ModuleType | Any = _kwal,
    funding_timeout: float = FUNDING_TIMEOUT,
    payment_timeout: float = PAYMENT_TIMEOUT,
) -> AsyncIterator[Event]:
    """Stream the 3.5 events for one covered purchase.

    Ends after `refused` when a rule fails. Emits `needs_approval` and raises
    `NeedsApproval` when the score band is the only thing in the way. Raises
    `PaymentFailed` after an `error` event if funding or the payment fails.
    """
    chain = _resolve_chain(chain)
    b = bought(q)
    rid = await asyncio.to_thread(chain.request_id, request)

    def event(step: str, status: str, purchase_id: int = 0, **kw) -> Event:
        return Event(purchase_id=purchase_id, step=step, status=status, request_id=rid, **kw)

    async with _payment_lock():
        names = from_bitmask(await asyncio.to_thread(chain.check, request, signature, b))
        if names == ["needs_approval"]:
            yield event("needs_approval", "waiting", detail=f"Needs your OK: {_usdc(q.charge_usdc)} at {q.shop}")
            raise NeedsApproval(rid)
        if names:
            yield event("refused", "error", detail=refusal_detail(names))
            return
        yield event("checked", "ok", detail=f"{q.title} at {q.shop}, {_usdc(q.charge_usdc)}")

        try:
            released = await asyncio.to_thread(chain.release, request, signature, b)
        except Exception as exc:  # noqa: BLE001 - a rule changed between check and release
            rule = getattr(exc, "rule", None)
            if rule == "needs_approval":
                yield event("needs_approval", "waiting", detail=f"Needs your OK: {_usdc(q.charge_usdc)} at {q.shop}")
                raise NeedsApproval(rid) from exc
            if rule:
                yield event("refused", "error", detail=refusal_detail([rule]))
                return
            raise
        pid = released.purchase_id
        yield event("released", "ok", pid, tx_hash=released.tx_hash, detail=f"{_usdc(q.charge_usdc)} sent to your Kwal vault")
        yield event("fee_taken", "ok", pid, tx_hash=released.tx_hash, detail=f"Cover fee {_usdc(released.fee_usdc)} from the maker")
        async for e in _settle(chain, kwal, q, pid, event, funding_timeout, payment_timeout):
            yield e


async def pay_approved(
    request: dict,
    signature: str,
    approval: dict,
    approval_sig: str,
    q: Quote,
    *,
    chain: Optional[Checkpoint] = None,
    kwal: ModuleType | Any = _kwal,
    funding_timeout: float = FUNDING_TIMEOUT,
    payment_timeout: float = PAYMENT_TIMEOUT,
) -> AsyncIterator[Event]:
    """A5 fallback: Ana approved this one herself (`guard.make_approval`, signed
    in her wallet). `releaseApproved`: her limits still apply, the score band
    and the Bond don't, so it is NOT covered: no fee, and no claim refund."""
    chain = _resolve_chain(chain)
    b = bought(q)
    rid = await asyncio.to_thread(chain.request_id, request)

    def event(step: str, status: str, purchase_id: int = 0, **kw) -> Event:
        return Event(purchase_id=purchase_id, step=step, status=status, request_id=rid, **kw)

    if str(approval.get("requestDigest", "")).lower() != rid.lower():
        yield event("refused", "error", detail="Refused: the approval is for a different request")
        return
    if int(approval.get("chargeUsdc", -1)) != int(q.charge_usdc):
        yield event("refused", "error", detail="Refused: the approval is for a different amount")
        return

    async with _payment_lock():
        try:
            released = await asyncio.to_thread(chain.release_approved, request, signature, approval, approval_sig, b)
        except Exception as exc:  # noqa: BLE001
            rule = getattr(exc, "rule", None)
            if rule or getattr(exc, "error", None) == "BadApproval":
                detail = refusal_detail([rule]) if rule else "Refused: approval expired or not signed by you"
                yield event("refused", "error", detail=detail)
                return
            raise
        pid = released.purchase_id
        yield event("released", "ok", pid, tx_hash=released.tx_hash,
                    detail=f"{_usdc(q.charge_usdc)} sent to your Kwal vault (you approved it; not covered)")
        async for e in _settle(chain, kwal, q, pid, event, funding_timeout, payment_timeout):
            yield e


async def _settle(chain, kwal, q: Quote, pid: int, event, funding_timeout: float, payment_timeout: float):
    """After release: vault funding -> Kwal checkout -> payment -> confirm."""

    async def fail(step: str, detail: str, *, confirm: bool, payment_id: Optional[str] = None):
        tx = None
        if confirm:
            tx = await asyncio.to_thread(chain.confirm, pid, payment_id_hash(payment_id or ""), FAILED)
        return event(step, "error", pid, tx_hash=tx, kwal_payment_id=payment_id, detail=detail)

    # Funding: Kwal needs ~38 s to see a contract transfer, "processing" meanwhile.
    yield event("funded", "waiting", pid, detail="Waiting for the vault to see the USDC")
    funding = await asyncio.to_thread(kwal.wait_for_funding, q.quote_id, funding_timeout)
    if funding.state != "ready":
        yield await fail("funded", f"Vault not ready after {funding_timeout:.0f} s ({funding.state})", confirm=True)
        raise PaymentFailed(f"funding {funding.state}", pid, confirmed=True)
    yield event("funded", "ok", pid, detail="Vault funded")

    try:
        submitted = await asyncio.to_thread(kwal.checkout, q.quote_id)
    except QuoteNotPayable as exc:  # expired or used: nothing was paid
        yield await fail("paid", f"Checkout refused: {exc}", confirm=True)
        raise PaymentFailed(str(exc), pid, confirmed=True) from exc
    payment_id = submitted.payment_id
    yield event("paid", "waiting", pid, kwal_payment_id=payment_id, detail="Paying the shop")

    final = await asyncio.to_thread(kwal.wait_for_payment, payment_id, payment_timeout, quote_id=q.quote_id)
    if final.state in ("declined", "error"):
        reason = getattr(final, "reason", None) or final.state
        yield await fail("paid", f"Payment {final.state}: {reason}", confirm=True, payment_id=payment_id)
        raise PaymentFailed(f"payment {final.state}", pid, confirmed=True)
    if final.state != "completed":  # still pending, or an approval link: outcome unknown, don't confirm
        url = getattr(final, "approval_url", None)
        detail = f"Payment {final.state}" + (f", approve at {url}" if url else "")
        yield event("paid", "error", pid, kwal_payment_id=payment_id, detail=detail)
        raise PaymentFailed(f"payment {final.state}", pid)
    yield event("paid", "ok", pid, kwal_payment_id=payment_id, detail="Paid")

    tx = await asyncio.to_thread(chain.confirm, pid, payment_id_hash(payment_id), PAID)
    yield event("confirmed", "ok", pid, tx_hash=tx, kwal_payment_id=payment_id, detail="Recorded on the Checkpoint")
