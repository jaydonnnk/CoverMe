"""spend_ceiling_cents: laeria's single min() over every limit and the backing."""
from __future__ import annotations

from service.guard.ceiling import cover_cents, spend_ceiling_cents
from service.guard.rules import Limits

from .helpers import limits, quote, request

PLENTY = 1_000 * 1_000_000  # 1,000 USDC of free cover


def test_ceiling_equals_the_quote_when_everything_has_headroom():
    assert spend_ceiling_cents(request(), quote(4_999), limits(), PLENTY) == 4_999


def test_each_limit_can_be_the_binding_one():
    q = quote(9_000)
    assert spend_ceiling_cents(request(maxUsdCents=6_000), q, limits(), PLENTY) == 6_000
    assert spend_ceiling_cents(request(), q, limits(per_item_max_cents=7_000), PLENTY) == 7_000
    assert spend_ceiling_cents(request(), q, limits(spent_this_month_cents=45_000), PLENTY) == 5_000
    assert spend_ceiling_cents(request(), q, limits(), 30 * 1_000_000) == 3_000


def test_unset_limits_give_zero_and_never_negative():
    assert spend_ceiling_cents(request(), quote(1_000), Limits(), PLENTY) == 0
    over = limits(spent_this_month_cents=60_000)
    assert spend_ceiling_cents(request(), quote(1_000), over, PLENTY) == 0
    assert spend_ceiling_cents(request(maxUsdCents=None), quote(1_000), limits(), PLENTY) == 0


def test_cover_leaves_room_for_the_fee():
    """Bond.reserve needs free cover >= charge + fee. 100 USDC at 50 bps backs 99.50."""
    assert cover_cents(100 * 1_000_000, fee_bps=50) == 9_950
    assert cover_cents(100 * 1_000_000) == 10_000
    assert cover_cents(0) == 0


def test_shipping_is_inside_the_ceiling():
    """Kwal's total includes shipping, so the quote term is the charge, not the listing."""
    q = quote(4_999, charge_usdc=80_620_000)
    assert spend_ceiling_cents(request(), q, limits(), PLENTY) == 8_062
