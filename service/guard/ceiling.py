"""The most a purchase may move, in cents.

Ported from laeria `api/routes/actions.py:345-361`: every limit that bounds the
spend goes into one `min()`, including the money that backs it, so "the payment
is covered" is a property of the code and not a separate check someone can skip.

What changed for Cover:
- laeria padded the live price (x1.05 plus a shipping buffer) because the card
  total was unknown until checkout. A Kwal quote already includes shipping and
  tax, so the quote term is exact: `rules.purchase_cents(q)`.
- laeria's stablecoin backing is the maker's free cover in the Bond, net of the
  cover fee, because `Bond.reserve` needs free cover >= charge + fee.
- Everything is integer cents. USDC converts at 10,000 units per cent; cover is
  rounded DOWN so it is never overstated.

The service pays only if `purchase_cents(q) <= spend_ceiling_cents(...)`.
"""
from __future__ import annotations

from .rules import USDC_UNITS_PER_CENT, Limits, QuoteLike, _cap, purchase_cents

BPS = 10_000


def cover_cents(free_cover_usdc: int, fee_bps: int = 0) -> int:
    """The largest charge the maker's free cover can back once the fee is taken."""
    if free_cover_usdc <= 0:
        return 0
    max_charge_usdc = int(free_cover_usdc) * BPS // (BPS + int(fee_bps))
    return max_charge_usdc // USDC_UNITS_PER_CENT


def spend_ceiling_cents(
    request: dict, q: QuoteLike, limits: Limits, free_cover_usdc: int, *, fee_bps: int = 0
) -> int:
    """min(Ana's signed max, the quote, her per-item cap, her monthly headroom,
    the maker's free cover). Unset limits contribute 0. Never negative."""
    headrooms = [
        _cap(request.get("maxUsdCents")),
        purchase_cents(q),
        _cap(limits.per_item_max_cents),
        _cap(limits.monthly_max_cents) - _cap(limits.spent_this_month_cents),
        cover_cents(free_cover_usdc, fee_bps),
    ]
    return max(min(headrooms), 0)
