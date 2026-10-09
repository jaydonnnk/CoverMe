"""Ana's limits against one quote: every rule that fails, by name.

Ported from laeria `PaymentService.verify_within_mandate`
(`backend/services/payment.py:53`) and `ActionMandate`
(`backend/core/models.py:121`). The safety property is the same one laeria
pinned after two shipped bypasses:

    An unset limit means NO ALLOWANCE, never unlimited.

`Limits(...)` built from a missing or empty Checkpoint row denies everything.
A cap of 0 is zero allowance; there is no way to express "unlimited".

What changed for Cover:
- laeria raised on the first violation. The refusal beat needs every failure
  at once ("Refused: amount, shop, address"), so `check_rules` returns them all,
  named exactly as the Checkpoint's custom errors (3.6) and in the same order.
- laeria's category allowlist and vendor blocklist became Ana's shop allowlist
  plus the shop she signed. Cover has no categories (open decision at J1).
- laeria's "require confirmation above" threshold is the agent's auto-pay limit
  from its score band (`Checkpoint.autoPayLimitCents`). Above it the purchase
  parks for Ana's approval (A5) instead of failing: `needs_approval`.
- laeria's approved-amount clamp is Ana's signed `maxUsdCents`, compared
  exactly with no tolerance.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Iterable, Optional, Protocol

# Bit i of Checkpoint.check()'s bitmask is RULES[i]. Append only; never reorder.
RULES: tuple[str, ...] = (
    "over_request_max",   # OverRequestMax: above the max Ana signed for this request
    "over_per_item",      # OverPerItem
    "over_monthly",       # OverMonthly
    "shop_not_allowed",   # ShopNotAllowed: not in her list, or not the shop she signed
    "wrong_address",      # WrongAddress: signed addressHash is not her saved address
    "expired",            # Expired: request deadline or her limits have ended
    "bad_signature",      # BadSignature (signing.verify_request)
    "not_enough_cover",   # NotEnoughCover (ceiling: the maker's free cover)
    "needs_approval",     # NeedsApproval (above the agent's auto-pay limit)
)
BIT = {name: 1 << i for i, name in enumerate(RULES)}

ZERO_HASH = "0x" + "0" * 64
USDC_UNITS_PER_CENT = 10_000  # 6-decimal USDC; 1 USD = 1 USDC = 100 cents


class QuoteLike(Protocol):  # the fields of 3.1 Quote the guard reads
    shop: str
    listed_usd_cents: int
    charge_usdc: int


@dataclass
class Limits:  # 3.2; read from the Checkpoint by chain.get_limits(shopper)
    per_item_max_cents: int = 0
    monthly_max_cents: int = 0
    shops: list[str] = field(default_factory=list)
    address_hash: str = ""
    ends_at: int = 0
    spent_this_month_cents: int = 0


def to_bitmask(names: Iterable[str]) -> int:
    mask = 0
    for name in names:
        mask |= BIT[name]
    return mask


def from_bitmask(mask: int) -> list[str]:
    """Decode Checkpoint.check(). Unknown bits are reported, never dropped."""
    names = [name for name, bit in BIT.items() if mask & bit]
    extra = mask & ~to_bitmask(RULES)
    i = 0
    while extra:
        if extra & 1:
            names.append(f"unknown_bit_{i}")
        extra >>= 1
        i += 1
    return names


def usdc_to_cents(usdc: int) -> int:
    """USDC units -> cents, rounded UP, so a charge is never understated."""
    return -(-int(usdc) // USDC_UNITS_PER_CENT)


def cents_to_usdc(cents: int) -> int:
    return int(cents) * USDC_UNITS_PER_CENT


def purchase_cents(q: QuoteLike) -> int:
    """The amount every limit compares: the larger of the shop's listed price
    and what the vault is actually charged (item + shipping + tax).

    Real pricing: the total wins, so shipping can't slip past Ana's limits.
    Sandbox pricing (1 USDC per item): the listed price wins, so a $6,799 item
    is still refused. Proposed at J1; if we agree "listed only", change this.
    """
    return max(int(q.listed_usd_cents), usdc_to_cents(q.charge_usdc))


def _cap(value: Optional[int]) -> int:
    """None and 0 are both zero allowance."""
    return int(value) if value else 0


def _hash(value) -> str:
    if isinstance(value, (bytes, bytearray)):
        value = "0x" + bytes(value).hex()
    value = (value or "").lower()
    return value if value.startswith("0x") else "0x" + value


def check_rules(request: dict, q: QuoteLike, limits: Limits, *, now: Optional[int] = None) -> list[str]:
    """Every failed rule, in RULES order; [] means pass. Unset means deny.

    Does not verify the signature (signing.verify_request) or the maker's cover
    (ceiling.spend_ceiling_cents), and does not decide approval (needs_approval).
    """
    now = int(time.time()) if now is None else int(now)
    amount = purchase_cents(q)
    failed: list[str] = []

    signed_max = _cap(request.get("maxUsdCents"))
    if signed_max <= 0 or amount > signed_max:
        failed.append("over_request_max")

    per_item = _cap(limits.per_item_max_cents)
    if per_item <= 0 or amount > per_item:
        failed.append("over_per_item")

    monthly = _cap(limits.monthly_max_cents)
    spent = _cap(limits.spent_this_month_cents)
    if monthly <= 0 or spent + amount > monthly:
        failed.append("over_monthly")

    shop = (q.shop or "").strip().lower()
    allowed = {s.strip().lower() for s in (limits.shops or []) if s and s.strip()}
    signed_shop = (request.get("shop") or "").strip().lower()
    if not shop or shop not in allowed or (signed_shop and signed_shop != shop):
        failed.append("shop_not_allowed")

    saved = _hash(limits.address_hash)
    if saved in ("0x", ZERO_HASH) or _hash(request.get("addressHash")) != saved:
        failed.append("wrong_address")

    deadline = _cap(request.get("deadline"))
    ends_at = _cap(limits.ends_at)
    if deadline <= now or ends_at <= now:
        failed.append("expired")

    return failed


def needs_approval(q: QuoteLike, auto_pay_limit_cents: Optional[int]) -> bool:
    """True when the purchase must park for Ana's approval (A5) rather than
    auto-pay. No known limit means approval: the absence of a rule cannot be
    what authorises silent execution. This never refuses: Ana's limits still
    apply to an approved purchase (check_rules)."""
    if auto_pay_limit_cents is None:
        return True
    return purchase_cents(q) > int(auto_pay_limit_cents)
