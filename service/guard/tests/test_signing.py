"""verify_request against the shared EIP-712 schema, with throwaway keys."""
from __future__ import annotations

import json

import pytest
from eth_account import Account

from service.guard.signing import (
    BadSignature,
    SigningConfigError,
    sign_request,
    verify_request,
)

from .helpers import request

CHECKPOINT = "0x00000000000000000000000000000000c0FFee01"
OTHER_CONTRACT = "0x00000000000000000000000000000000c0FFee02"


@pytest.fixture
def ana():
    return Account.create()


def signed(acct, **overrides):
    req = request(shopper=acct.address, **overrides)
    return req, sign_request(req, acct.key.hex(), verifying_contract=CHECKPOINT)


def test_recovers_the_shopper(ana):
    req, sig = signed(ana)
    assert verify_request(req, sig, verifying_contract=CHECKPOINT) == ana.address


def test_js_style_decimal_strings_verify(ana):
    req, sig = signed(ana)
    as_json = {k: (str(v) if isinstance(v, int) else v) for k, v in req.items()}
    assert verify_request(as_json, sig, verifying_contract=CHECKPOINT) == ana.address


@pytest.mark.parametrize("field,value", [
    ("colour", "white/dune"), ("maxUsdCents", 9_999_999), ("shop", "keychron.com"),
    ("addressHash", "0x" + "cd" * 32), ("nonce", 2), ("agentId", 2),
])
def test_any_changed_field_fails(ana, field, value):
    req, sig = signed(ana)
    with pytest.raises(BadSignature, match="not signed by its shopper"):
        verify_request({**req, field: value}, sig, verifying_contract=CHECKPOINT)


def test_signed_by_someone_else_fails(ana):
    req = request(shopper=ana.address)
    sig = sign_request(req, Account.create().key.hex(), verifying_contract=CHECKPOINT)
    with pytest.raises(BadSignature):
        verify_request(req, sig, verifying_contract=CHECKPOINT)


def test_other_contract_domain_fails(ana):
    req, sig = signed(ana)
    with pytest.raises(BadSignature):
        verify_request(req, sig, verifying_contract=OTHER_CONTRACT)


def test_missing_unknown_and_malformed_fields_fail(ana):
    req, sig = signed(ana)
    with pytest.raises(BadSignature, match="missing"):
        verify_request({k: v for k, v in req.items() if k != "deadline"}, sig,
                       verifying_contract=CHECKPOINT)
    with pytest.raises(BadSignature, match="not signed"):
        verify_request({**req, "quantity": 3}, sig, verifying_contract=CHECKPOINT)
    with pytest.raises(BadSignature, match="32 bytes"):
        verify_request({**req, "addressHash": "0x1234"}, sig, verifying_contract=CHECKPOINT)
    with pytest.raises(BadSignature, match="integer"):
        verify_request({**req, "nonce": True}, sig, verifying_contract=CHECKPOINT)


def test_garbage_signature_fails(ana):
    req, _ = signed(ana)
    with pytest.raises(BadSignature):
        verify_request(req, "0x" + "00" * 65, verifying_contract=CHECKPOINT)
    with pytest.raises(BadSignature):
        verify_request(req, "not-a-signature", verifying_contract=CHECKPOINT)


def test_placeholder_contract_is_never_used(ana):
    req = request(shopper=ana.address)
    with pytest.raises(SigningConfigError):
        sign_request(req, ana.key.hex(), verifying_contract="<Checkpoint address>")


def test_undeployed_checkpoint_refuses(ana, tmp_path, monkeypatch):
    path = tmp_path / "deployments.json"
    path.write_text(json.dumps({"cover": {"Checkpoint": {"address": None, "abi": []}}}))
    monkeypatch.setenv("DEPLOYMENTS_FILE", str(path))
    with pytest.raises(SigningConfigError):
        verify_request(request(shopper=ana.address), "0x" + "00" * 65)


def test_reads_the_deployed_checkpoint(ana, tmp_path, monkeypatch):
    path = tmp_path / "deployments.json"
    path.write_text(json.dumps({"cover": {"Checkpoint": {"address": CHECKPOINT, "abi": []}}}))
    monkeypatch.setenv("DEPLOYMENTS_FILE", str(path))
    req, sig = signed(ana)
    assert verify_request(req, sig) == ana.address
