"""laeria's 19 mandate tests (`backend/tests/test_mandate.py`), ported to Cover.

Each test keeps laeria's intent and names its origin. Amounts are cents.
Where Cover deliberately differs, the docstring says so:
- autonomy on/off and the confirm threshold -> `needs_approval` with the
  agent's auto-pay limit (score band);
- categories and blocked vendors -> Ana's shop allowlist and the shop she signed;
- an empty shop list DENIES (laeria permitted any category): unset means deny;
- the approved amount is Ana's signed `maxUsdCents`, exact, no tolerance.

These cases are also the list J5 re-runs against Checkpoint.sol.
"""
from __future__ import annotations

import pytest

from service.guard.rules import Limits, check_rules, needs_approval

from .helpers import NOW, limits, quote, request


def rules(lim, q, **req):
    return check_rules(request(**req), q, lim, now=NOW)


# ---- the master switch -> the auto-pay limit ----

def test_autonomy_off_always_needs_confirmation():
    """laeria 1. A $0 auto-pay limit (score under 60) parks every purchase."""
    assert needs_approval(quote(100), 0) is True


def test_autonomy_off_does_not_raise_even_when_over_cap():
    """laeria 2. Parking is "ask Ana", not a refusal. Cover adds: approval
    does not lift her limits, so check_rules still reports the cap."""
    q = quote(1_000_000)
    assert needs_approval(q, 0) is True
    assert "over_per_item" in rules(limits(), q)


# ---- REGRESSION: unset limits must deny, never permit ----

def test_empty_mandate_denies_everything():
    """laeria 3. `Limits()` is what a missing Checkpoint row produces."""
    failed = rules(Limits(), quote(1))
    assert {"over_per_item", "over_monthly", "shop_not_allowed",
            "wrong_address", "expired"} <= set(failed)


def test_unset_per_transaction_denies():
    """laeria 4."""
    assert "over_per_item" in rules(limits(per_item_max_cents=None), quote(100))


def test_unset_monthly_denies():
    """laeria 5."""
    assert "over_monthly" in rules(limits(monthly_max_cents=None), quote(100))


def test_unset_confirm_threshold_confirms_rather_than_executes():
    """laeria 6. An unknown auto-pay limit means approval, not auto-pay."""
    assert needs_approval(quote(100), None) is True


def test_zero_cap_is_zero_allowance_not_unlimited():
    """laeria 7. One cent against a 0 cap fails."""
    assert rules(limits(per_item_max_cents=0), quote(1)) == ["over_per_item"]


# ---- per-item cap boundary ----

@pytest.mark.parametrize(
    "cents,expect_fail",
    [(9_999, False), (10_000, False), (10_001, True), (1_000_000, True)],
)
def test_per_transaction_boundary(cents, expect_fail):
    """laeria 8. The cap is inclusive."""
    failed = rules(limits(monthly_max_cents=10_000_000), quote(cents))
    assert ("over_per_item" in failed) is expect_fail
    if not expect_fail:
        assert failed == []


# ---- monthly cap counts prior spend ----

def test_monthly_cap_counts_prior_spend():
    """laeria 9."""
    assert rules(limits(spent_this_month_cents=44_900), quote(5_000)) == []
    assert rules(limits(spent_this_month_cents=45_100), quote(5_000)) == ["over_monthly"]


def test_monthly_cap_exact_boundary_allowed():
    """laeria 10."""
    assert rules(limits(spent_this_month_cents=45_000), quote(5_000)) == []


# ---- the auto-pay limit parks rather than executing ----

def test_above_confirm_threshold_parks():
    """laeria 11."""
    assert needs_approval(quote(2_600), 2_500) is True


def test_at_confirm_threshold_executes():
    """laeria 12. The limit is inclusive."""
    assert needs_approval(quote(2_500), 2_500) is False


# ---- category / vendor scoping -> shops ----

def test_category_not_in_allowlist_denies():
    """laeria 13. A shop outside Ana's list fails."""
    failed = rules(limits(), quote(1_000, shop="casino.example"), shop="")
    assert failed == ["shop_not_allowed"]


def test_empty_allowlist_permits_any_category():
    """laeria 14, INVERTED on purpose: laeria let an empty list allow any
    category. In Cover an empty shop list is an unset limit, so it denies."""
    assert rules(limits(shops=[]), quote(1_000)) == ["shop_not_allowed"]


def test_blocked_vendor_denies():
    """laeria 15. The shop Ana signed binds: another shop on her list still fails."""
    lim = limits(shops=["twelvesouth.com", "keychron.com"])
    failed = rules(lim, quote(1_000, shop="keychron.com"), shop="twelvesouth.com")
    assert failed == ["shop_not_allowed"]


def test_unblocked_vendor_passes():
    """laeria 16. Matching shop, on the list, case-insensitive."""
    assert rules(limits(shops=["TwelveSouth.com"]), quote(1_000), shop="twelvesouth.com") == []


# ---- REGRESSION: consent binds to an amount ----
#
# laeria clamped execution to the figure a human approved, even when the live
# price was inside the standing caps. In Cover that figure is the maxUsdCents
# Ana signed, compared exactly.

def test_price_drift_math_reparks_beyond_tolerance():
    """laeria 17. $400 live against a $50 signed max fails."""
    lim = limits(per_item_max_cents=100_000, monthly_max_cents=1_000_000)
    assert rules(lim, quote(40_000), maxUsdCents=5_000) == ["over_request_max"]


def test_price_drift_math_allows_within_tolerance():
    """laeria 18. Cover has no tolerance: at the signed max passes, one cent over fails."""
    assert rules(limits(), quote(5_000), maxUsdCents=5_000) == []
    assert rules(limits(), quote(5_001), maxUsdCents=5_000) == ["over_request_max"]


def test_drifted_price_can_still_satisfy_the_standing_mandate():
    """laeria 19. Why the signed max exists: $400 passes a $500 per-item cap,
    so Ana's limits alone would let a $50 request buy at $400."""
    lim = limits(per_item_max_cents=50_000, monthly_max_cents=500_000)
    assert rules(lim, quote(40_000), maxUsdCents=1_000_000) == []
    assert rules(lim, quote(40_000), maxUsdCents=5_000) == ["over_request_max"]
