"""Cover-only rules: all failures together, the bitmask, expiry, address and pricing."""
from __future__ import annotations

from service.guard.rules import (
    RULES,
    check_rules,
    from_bitmask,
    purchase_cents,
    to_bitmask,
    usdc_to_cents,
)

from .helpers import ADDRESS_HASH, NOW, limits, quote, request


def test_refusal_beat_reports_amount_shop_and_address_together():
    req = request(maxUsdCents=6_000, shop="", addressHash="0x" + "cd" * 32)
    failed = check_rules(req, quote(679_900, shop="gmktec.com"), limits(), now=NOW)
    assert failed == ["over_request_max", "over_per_item", "over_monthly",
                      "shop_not_allowed", "wrong_address"]


def test_bitmask_round_trip_and_stable_positions():
    assert RULES[:6] == ("over_request_max", "over_per_item", "over_monthly",
                         "shop_not_allowed", "wrong_address", "expired")
    names = ["over_request_max", "shop_not_allowed", "wrong_address"]
    assert to_bitmask(names) == 0b11001
    assert from_bitmask(0b11001) == names
    assert from_bitmask(1 << 20) == ["unknown_bit_20"]


def test_expired_request_deadline():
    assert check_rules(request(deadline=NOW), quote(1_000), limits(), now=NOW) == ["expired"]


def test_limits_that_have_ended():
    assert check_rules(request(), quote(1_000), limits(ends_at=NOW - 1), now=NOW) == ["expired"]


def test_address_hash_compare_is_case_insensitive_and_zero_denies():
    assert check_rules(request(addressHash=ADDRESS_HASH.upper().replace("0X", "0x")),
                       quote(1_000), limits(), now=NOW) == []
    zero = "0x" + "00" * 32
    assert check_rules(request(addressHash=zero), quote(1_000),
                       limits(address_hash=zero), now=NOW) == ["wrong_address"]


def test_shipping_counts_against_the_signed_max():
    """PowerBug to the US: listed $49.99, charged $61.54. "Under $60" fails."""
    q = quote(4_999, charge_usdc=61_540_000)
    assert purchase_cents(q) == 6_154
    assert check_rules(request(maxUsdCents=6_000), q, limits(), now=NOW) == ["over_request_max"]
    assert check_rules(request(maxUsdCents=9_000), q, limits(), now=NOW) == []


def test_sandbox_pricing_cannot_hide_the_listed_price():
    """If the gateway charges 1 USDC per item, the $6,799 listing still refuses."""
    q = quote(679_900, charge_usdc=1_000_000)
    assert purchase_cents(q) == 679_900
    assert "over_per_item" in check_rules(request(), q, limits(), now=NOW)


def test_usdc_to_cents_rounds_up():
    assert usdc_to_cents(61_540_000) == 6_154
    assert usdc_to_cents(61_540_001) == 6_155
    assert usdc_to_cents(0) == 0
