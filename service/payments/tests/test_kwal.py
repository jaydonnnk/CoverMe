"""service.payments.kwal against recorded Kwal runs. No network.

`hmx-quote` is a real run recorded 9 Oct (catalogue reads, variant
resolution, one HMX quote to a fictional US address, one funding read).
Tests that build their own fixtures say so. Tests that need the Kwal skill's
parsers skip when the skill isn't installed (CI); ShipTo tests always run.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from service.payments import kwal

RUN = Path(__file__).resolve().parents[2] / "fixtures" / "kwal" / "hmx-quote"
HMX = "prd_8e2fe57511394d6c9139ea87fa10471d"
SISU = "prd_bc7c360929de4980ae77aab82a8ca557"
HMX_VARIANT = "var_1a838a2d6fcf45a7ad28fadb590daa5a"
QUOTE_ID = "594bc246-7f13-44bc-b495-02d276122689"

ANA = dict(
    first_name="Ana",
    last_name="Test",
    phone="+14155550123",
    line1="1 Ferry Building",
    city="San Francisco",
    region="CA",
    postal_code="94111",
    country="US",
    email="ana.test@example.com",
)


@pytest.fixture
def skill():
    try:
        return kwal.skill()
    except kwal.KwalError:
        pytest.skip("Kwal skill not installed")


@pytest.fixture
def replay(skill, monkeypatch):
    monkeypatch.setattr(kwal, "_sleep", lambda seconds: None)

    def load(directory):
        kwal.use_replay(directory)

    yield load
    kwal.use_replay(None)


def _copy_run(tmp_path: Path, edit=None) -> Path:
    """A copy of the recorded run, optionally edited per file."""
    target = tmp_path / "run"
    shutil.copytree(RUN, target)
    if edit:
        for file in sorted(target.glob("*.json")):
            record = json.loads(file.read_text(encoding="utf-8"))
            edit(file.name, record)
            file.write_text(json.dumps(record), encoding="utf-8")
    return target


def _write(directory: Path, name: str, method: str, path: str, response=None, error=None) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    record = {"method": method, "path": path, "request": None, "response": response, "error": error}
    (directory / name).write_text(json.dumps(record), encoding="utf-8")


# ------------------------------------------------------------------ ShipTo


def test_ship_to_normalises_and_hashes_deterministically():
    a = kwal.ShipTo(**ANA)
    b = kwal.ShipTo(**{**ANA, "country": " us ", "email": "Ana.Test@Example.com", "city": " San Francisco "})
    assert a == b
    assert a.canonical_json().startswith('{"city":"San Francisco","country":"US",')
    assert a.address_hash() == b.address_hash()
    assert a.address_hash().startswith("0x") and len(a.address_hash()) == 66
    assert kwal.ShipTo(**{**ANA, "line2": "Suite 1"}).address_hash() != a.address_hash()


def test_ship_to_rejects_bad_input():
    with pytest.raises(ValueError, match="E.164"):
        kwal.ShipTo(**{**ANA, "phone": "415-555-0123"})
    with pytest.raises(ValueError, match="needs last_name"):
        kwal.ShipTo(**{**ANA, "last_name": " "})
    with pytest.raises(ValueError, match="ISO-2"):
        kwal.ShipTo(**{**ANA, "country": "USA"})
    with pytest.raises(ValueError, match="unknown fields: name"):
        kwal.ShipTo.from_json({**ANA, "name": "Ana Test"})


def test_ship_to_kwal_address_omits_empty_optionals():
    address = kwal.ShipTo.from_json(json.dumps({**ANA, "region": ""})).kwal_address()
    assert address == {
        "firstName": "Ana",
        "lastName": "Test",
        "phone": "+14155550123",
        "line1": "1 Ferry Building",
        "city": "San Francisco",
        "postalCode": "94111",
        "country": "US",
    }


def test_quantity_must_be_one():
    with pytest.raises(ValueError, match="quantity must be 1"):
        kwal.quote(HMX_VARIANT, 2, kwal.ShipTo(**ANA))


def test_option_names_map_to_signed_fields():
    assert kwal._field_names(["Color", "Size"]) == {"Color": "colour", "Size": "size"}
    assert kwal._field_names(["Colour", "Style", "Switch"]) == {
        "Colour": "colour",
        "Style": "model",
        "Switch": "switch",
    }


# ---------------------------------------------------- recorded run (replay)


def test_options_are_lowercased_labels(replay):
    replay(RUN)
    kwal.search("HMX Snowflake", limit=3)
    assert kwal.options(HMX) == {"size": ["18 set"]}
    assert kwal.options(SISU) == {
        "colour": ["hot pink", "intense red", "neon flash", "royal blue", "snow white", "charcoal black"]
    }


def test_search_reports_shop_and_cents(replay):
    replay(RUN)
    found = kwal.search("HMX Snowflake", limit=3)
    assert found[0].title == "HMX Snowflake Linear Switches"
    assert found[0].shop == "divinikey"
    assert found[0].listed_usd_cents == 630  # Kwal states 63 with 1 decimal


def test_variant_matches_labels_case_insensitively(replay):
    replay(RUN)
    kwal.options(HMX)
    kwal.options(SISU)
    assert kwal.variant(SISU, {"Colour": "Snow White"}) == "var_4bd8019757e24fecbd37ee4f0af74a31"
    with pytest.raises(kwal.KwalError, match="not a colour"):
        kwal.variant(SISU, {"colour": "black"})  # exact labels only: "charcoal black"
    with pytest.raises(kwal.KwalError, match="Choose a size"):
        kwal.variant(HMX, {})


def _quote_hmx():
    kwal.search("HMX Snowflake", limit=3)
    kwal.options(HMX)
    kwal.options(SISU)
    kwal.variant(SISU, {"colour": "snow white"})
    kwal.variant(SISU, {"colour": "charcoal black"})
    variant_id = kwal.variant(HMX, {"size": "18 set"})
    return kwal.quote(variant_id, 1, kwal.ShipTo(**ANA))


def test_quote_listed_is_item_price_and_charge_is_total(replay):
    replay(RUN)
    q = _quote_hmx()
    assert q == kwal.Quote(
        quote_id=QUOTE_ID,
        product_id=HMX,
        variant_id=HMX_VARIANT,
        shop="divinikey",
        title="HMX Snowflake Linear Switches",
        colour="",
        size="18 set",
        model="",
        image_url=None,
        listed_usd_cents=630,  # item
        charge_usdc=15_730_000,  # 6.30 + 8.18 shipping + 1.25 tax
        sandbox_pricing=False,
        expires_at=1_791_545_912,
    )


def test_funding_reads_vault_readiness(replay):
    replay(RUN)
    q = _quote_hmx()
    state = kwal.funding(q.quote_id)
    assert state.state == "ready"
    assert state.required.minor_units == q.charge_usdc
    assert state.vault_address == "0x2dF401bA23216Bc593D052697893554B55Eda0fb"


def test_unknown_variant_needs_product(replay):
    replay(RUN)
    with pytest.raises(kwal.KwalError, match="Unknown variant"):
        kwal.quote("var_never_resolved", 1, kwal.ShipTo(**ANA))


def test_sandbox_pricing_from_quote_id_prefix(replay, tmp_path):
    """Edited copy: the recorded quote with a sandbox id and a 1 USDC total."""

    def edit(name, record):
        if name.endswith("_POST_quotes.json"):
            record["response"]["quoteId"] = "sandbox_quote_abc"
            record["response"]["total"] = {"minorUnits": "100", "currency": "USD", "decimals": 2}

    replay(_copy_run(tmp_path, edit))
    q = _quote_hmx()
    assert q.sandbox_pricing is True
    assert q.charge_usdc == 1_000_000
    assert q.listed_usd_cents == 630  # the listing still drives the limits


def test_quote_already_used_is_not_payable(replay, tmp_path):
    """Edited copy: Reap hands back a basket's quote that a payment holds."""

    def edit(name, record):
        if name.endswith("_POST_quotes.json"):
            record["response"]["paymentId"] = "pay_earlier"

    replay(_copy_run(tmp_path, edit))
    with pytest.raises(kwal.QuoteNotPayable, match="pay_earlier"):
        _quote_hmx()


def test_missing_shipping_choice_takes_the_cheapest(replay, tmp_path):
    """Edited copy: no preselected option, so quote() selects ship_0 ($8.18)."""

    def edit(name, record):
        if name.endswith("_POST_quotes.json"):
            selected = dict(record["response"])
            del record["response"]["selectedShippingOptionId"]
            _write(tmp_path / "run", "0010a_POST_shipping.json", "POST",
                   f"/kwal/participant/v1/quotes/{QUOTE_ID}/shipping", response=selected)

    run = _copy_run(tmp_path, edit)
    replay(run)
    assert _quote_hmx().charge_usdc == 15_730_000
    assert any(kwal._replay.records[i]["path"].endswith("/shipping") for i in kwal._replay.used)


# ------------------------------------------------------------------ retries


def test_busy_provider_is_retried_then_succeeds(replay, tmp_path, monkeypatch):
    """Built fixture: two ParticipantUnavailable answers, then the recorded search."""
    run = tmp_path / "busy"
    busy = "GET /kwal/participant/v1/products?query=HMX+Snowflake&limit=3 failed with HTTP 503. (service_error=ParticipantUnavailable)"
    path = "/kwal/participant/v1/products?query=HMX+Snowflake&limit=3"
    _write(run, "0001.json", "GET", path, error=busy)
    _write(run, "0002.json", "GET", path, error=busy)
    _write(run, "0003.json", "GET", path, response=json.loads((RUN / "0001_GET_products.json").read_text())["response"])
    waits = []
    monkeypatch.setattr(kwal, "_sleep", waits.append)
    replay(run)
    assert kwal.search("HMX Snowflake", limit=3)[0].shop == "divinikey"
    assert len(waits) == 2 and all(15 <= w <= 30 for w in waits)


def test_retry_gives_up_after_five_minutes(skill, monkeypatch):
    clock = [0.0]
    monkeypatch.setattr(kwal, "_clock", lambda: clock[0])
    monkeypatch.setattr(kwal, "_sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds))
    calls = []

    def busy():
        calls.append(1)
        raise skill.errors.ServiceError("POST /x failed with HTTP 429.")

    with pytest.raises(kwal.KwalError, match="gave up after 5 minutes"):
        kwal._retry(busy)
    assert clock[0] <= kwal.RETRY_BUDGET_SECONDS
    assert 10 <= len(calls) <= 21  # 15-30 s apart inside 300 s


def test_retry_after_hint_is_respected(skill, monkeypatch):
    waits = []
    monkeypatch.setattr(kwal, "_sleep", waits.append)
    answers = iter([skill.errors.ServiceError("GET /x failed with HTTP 429. (retry_after=45s)")])

    def once():
        for error in answers:
            raise error
        return "ok"

    assert kwal._retry(once) == "ok"
    assert waits == [45.0]


def test_permanent_errors_are_not_retried(skill, monkeypatch):
    monkeypatch.setattr(kwal, "_sleep", lambda seconds: pytest.fail("slept"))

    def bad():
        raise skill.errors.ServiceError("POST /quotes failed with HTTP 400. (service_error=ParticipantBadRequest)")

    with pytest.raises(kwal.KwalError, match="ParticipantBadRequest"):
        kwal._retry(bad)


# ----------------------------------------------------------------- checkout


def _payment(state: str) -> dict:
    """Built from the skill's payment contract; no real checkout is recorded yet."""
    return {
        "paymentId": "pay_test",
        "quoteId": QUOTE_ID,
        "state": f"PARTICIPANT_PAYMENT_STATE_{state}",
        "step": "card_clearing",
        "charged": {"minorUnits": "15730000", "currency": "USDC", "decimals": 6},
    }


def test_unknown_checkout_outcome_is_read_back_not_resent(replay, tmp_path):
    """Built fixture: the POST never answers; the read-back finds the payment,
    so no second POST is sent (none is recorded, so one would fail)."""
    run = _copy_run(tmp_path)
    quote_body = json.loads((RUN / "0010_POST_quotes.json").read_text())["response"]
    _write(run, "0100.json", "GET", f"/kwal/participant/v1/quotes/{QUOTE_ID}", response=quote_body)
    _write(run, "0101.json", "POST", "/kwal/participant/v1/payments",
           error="POST /kwal/participant/v1/payments did not complete.")
    _write(run, "0102.json", "GET", "/kwal/participant/v1/payments/pay_test", response=_payment("COMPLETED"))
    replay(run)
    paid = kwal.checkout(QUOTE_ID, payment_id="pay_test")
    assert paid.state == "completed"
    assert paid.charged.minor_units == 15_730_000


def test_checkout_refuses_a_quote_held_by_another_payment(replay, tmp_path):
    run = tmp_path / "held"
    quote_body = json.loads((RUN / "0010_POST_quotes.json").read_text())["response"]
    _write(run, "0001.json", "GET", f"/kwal/participant/v1/quotes/{QUOTE_ID}",
           response={**quote_body, "paymentId": "pay_other"})
    replay(run)
    with pytest.raises(kwal.QuoteNotPayable, match="pay_other"):
        kwal.checkout(QUOTE_ID, payment_id="pay_test")


def test_wait_for_payment_polls_until_settled(replay, tmp_path):
    run = tmp_path / "poll"
    path = "/kwal/participant/v1/payments/pay_test"
    _write(run, "0001.json", "GET", path, response=_payment("PENDING"))
    _write(run, "0002.json", "GET", path, response=_payment("COMPLETED"))
    replay(run)
    assert kwal.wait_for_payment("pay_test").state == "completed"


def test_recording_redacts_ship_to_and_token(skill, tmp_path, monkeypatch):
    monkeypatch.setenv(kwal.FIXTURES_ENV, str(tmp_path))
    monkeypatch.setattr(kwal, "_run_dir", None)
    monkeypatch.setattr(kwal, "_private", set())
    kwal._remember_private(kwal.ShipTo(**ANA))
    kwal._private.add("secret-token")
    kwal._record("POST", "/kwal/participant/v1/quotes",
                  {"email": ANA["email"], "shippingAddress": {"line1": ANA["line1"], "country": "US"}},
                  {"echo": "Bearer secret-token", "city": "San Francisco"})
    text = next(tmp_path.rglob("*.json")).read_text()
    for private in (ANA["email"], ANA["line1"], "secret-token", "San Francisco"):
        assert private not in text
    assert '"country": "US"' in text
