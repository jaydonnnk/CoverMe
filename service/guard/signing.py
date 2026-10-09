"""Ana's signed purchase request: recover who signed it.

Ported from laeria `backend/services/delegation.py`. The idea carries over
unchanged: the agent's authority to spend traces to a signature Ana made
*beforehand*, and the guard rebuilds the EIP-712 typed data from its own
definition before recovering, so a client cannot change the field set the
signature is checked against.

What changed for Cover:
- The type definition is not written here. It is loaded from
  `shared/purchase-request.json`, the single source the app and the contract
  also use (CONTRIBUTING: no independent signing definitions).
- The domain binds the deployed Checkpoint (`verifyingContract`), read from
  `deployments/ink-sepolia.json`. The JSON placeholder is never signed or
  verified against.
- The recovered signer must be the request's own `shopper` field.
- Expiry is a rule (`expired` in rules.py), not a signature failure, so the
  refusal beat can report it next to the other rules.

Only plain ECDSA (EOA) signatures recover. ERC-1271 smart-account signatures
do not, which is why Ana's Privy wallet must be the embedded EOA.
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_FILE = ROOT / "shared" / "purchase-request.json"
DEFAULT_DEPLOYMENTS_FILE = "deployments/ink-sepolia.json"
ZERO_ADDRESS = "0x" + "0" * 40


class BadSignature(ValueError):
    """The request is malformed, or was not signed by its shopper."""


class SigningConfigError(RuntimeError):
    """The Checkpoint address is missing, so nothing can be verified yet."""


@lru_cache(maxsize=1)
def schema() -> dict:
    return json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))


def fields() -> list[dict]:
    s = schema()
    return s["types"][s["primaryType"]]


def checkpoint_address() -> str:
    """The deployed Checkpoint from the deployments file (`DEPLOYMENTS_FILE`)."""
    path = Path(os.environ.get("DEPLOYMENTS_FILE") or DEFAULT_DEPLOYMENTS_FILE)
    if not path.is_absolute():
        path = ROOT / path
    deployments = json.loads(path.read_text(encoding="utf-8"))
    address = (deployments.get("cover", {}).get("Checkpoint") or {}).get("address")
    if not address:
        raise SigningConfigError(
            f"no Checkpoint address in {path}; requests cannot be verified until it is deployed"
        )
    return address


def _domain(verifying_contract: str) -> dict:
    from eth_utils import is_address, to_checksum_address

    if not isinstance(verifying_contract, str) or not is_address(verifying_contract):
        raise SigningConfigError(
            f"verifyingContract {verifying_contract!r} is not an address; never sign the placeholder"
        )
    d = schema()["domain"]
    return {
        "name": d["name"],
        "version": d["version"],
        "chainId": int(d["chainId"]),
        "verifyingContract": to_checksum_address(verifying_contract),
    }


def _coerce(name: str, solidity_type: str, value):
    from eth_utils import is_address, to_checksum_address

    if solidity_type == "address":
        if not isinstance(value, str) or not is_address(value):
            raise BadSignature(f"{name} is not an address")
        return to_checksum_address(value)
    if solidity_type == "uint256":
        # JS sends bigints as decimal strings; bools are ints in Python, refuse them.
        if isinstance(value, bool) or not isinstance(value, (int, str)):
            raise BadSignature(f"{name} is not an integer")
        try:
            n = int(value)
        except ValueError as exc:
            raise BadSignature(f"{name} is not an integer") from exc
        if not 0 <= n < 2**256:
            raise BadSignature(f"{name} is out of range for uint256")
        return n
    if solidity_type == "bytes32":
        if isinstance(value, (bytes, bytearray)) and len(value) == 32:
            return bytes(value)
        if isinstance(value, str) and value.startswith("0x") and len(value) == 66:
            try:
                return bytes.fromhex(value[2:])
            except ValueError as exc:
                raise BadSignature(f"{name} is not 32 bytes of hex") from exc
        raise BadSignature(f"{name} is not 32 bytes of hex")
    if solidity_type == "string":
        if not isinstance(value, str):
            raise BadSignature(f"{name} is not a string")
        return value
    raise SigningConfigError(f"unsupported EIP-712 type {solidity_type!r} in the schema")


def message(request: dict) -> dict:
    """The request as the exact EIP-712 message. Missing or unknown fields are
    refused: everything downstream may rely on every field having been signed."""
    if not isinstance(request, dict):
        raise BadSignature("request is not an object")
    names = [f["name"] for f in fields()]
    missing = [n for n in names if n not in request]
    if missing:
        raise BadSignature(f"request is missing signed fields: {', '.join(missing)}")
    unknown = sorted(set(request) - set(names))
    if unknown:
        raise BadSignature(f"request has fields that are not signed: {', '.join(unknown)}")
    return {f["name"]: _coerce(f["name"], f["type"], request[f["name"]]) for f in fields()}


def signable(request: dict, verifying_contract: str):
    from eth_account.messages import encode_typed_data

    s = schema()
    return encode_typed_data(
        _domain(verifying_contract),
        {s["primaryType"]: fields()},
        message(request),
    )


def verify_request(request: dict, signature: str, *, verifying_contract: str | None = None) -> str:
    """Recover the EIP-712 signer of the 3.4 PurchaseRequest and return it
    (checksummed). Raises BadSignature unless the signer is `request.shopper`."""
    from eth_account import Account

    contract = verifying_contract or checkpoint_address()
    msg = signable(request, contract)
    try:
        signer = Account.recover_message(msg, signature=signature)
    except Exception as exc:  # noqa: BLE001 - any decode failure is a bad signature
        raise BadSignature(f"could not recover a signer from the signature: {exc}") from exc

    shopper = request["shopper"]
    if shopper.lower() == ZERO_ADDRESS:
        raise BadSignature("shopper is the zero address")
    if signer.lower() != shopper.lower():
        raise BadSignature(f"the request was not signed by its shopper ({signer} != {shopper})")
    return signer


def sign_request(request: dict, private_key: str, *, verifying_contract: str | None = None) -> str:
    """Sign as Ana from Python (tests, and demo_reset.py with ANA_PRIVATE_KEY)."""
    from eth_account import Account

    contract = verifying_contract or checkpoint_address()
    signed = Account.sign_message(signable(request, contract), private_key=private_key)
    return "0x" + signed.signature.hex().removeprefix("0x")


def request_digest(request: dict, *, verifying_contract: str | None = None) -> str:
    """The EIP-712 digest Ana signs (`Checkpoint.hashRequest`): the service's
    `request_id` for events before `release` gives a purchase id (J1 item 6),
    and the `requestDigest` of an A5 `Approval`."""
    from eth_utils import keccak

    msg = signable(request, verifying_contract or checkpoint_address())
    return "0x" + keccak(b"\x19" + msg.version + msg.header + msg.body).hex()


# ------------------------------------------------------------------ A5 approval

# Same domain as the request. Matches Checkpoint.APPROVAL_TYPEHASH; read from
# shared/purchase-request.json once J1 adds it there, this is the fallback.
APPROVAL_FIELDS = [
    {"name": "requestDigest", "type": "bytes32"},
    {"name": "chargeUsdc", "type": "uint256"},
    {"name": "deadline", "type": "uint256"},
]


def approval_fields() -> list[dict]:
    return schema().get("types", {}).get("Approval") or APPROVAL_FIELDS


def approval_message(approval: dict) -> dict:
    if not isinstance(approval, dict):
        raise BadSignature("approval is not an object")
    names = [f["name"] for f in approval_fields()]
    if sorted(approval) != sorted(names):
        raise BadSignature(f"approval must have exactly: {', '.join(names)}")
    return {f["name"]: _coerce(f["name"], f["type"], approval[f["name"]]) for f in approval_fields()}


def approval_signable(approval: dict, verifying_contract: str):
    from eth_account.messages import encode_typed_data

    return encode_typed_data(_domain(verifying_contract), {"Approval": approval_fields()}, approval_message(approval))


def make_approval(request: dict, charge_usdc: int, deadline: int, *, verifying_contract: str | None = None) -> dict:
    """The Approval Ana signs for one uncovered purchase (A5): it names this
    request's digest, so it dies with the request's nonce."""
    return {
        "requestDigest": request_digest(request, verifying_contract=verifying_contract),
        "chargeUsdc": int(charge_usdc),
        "deadline": int(deadline),
    }


def sign_approval(approval: dict, private_key: str, *, verifying_contract: str | None = None) -> str:
    from eth_account import Account

    signed = Account.sign_message(
        approval_signable(approval, verifying_contract or checkpoint_address()), private_key=private_key
    )
    return "0x" + signed.signature.hex().removeprefix("0x")


def verify_approval(
    approval: dict, signature: str, request: dict, *, verifying_contract: str | None = None
) -> str:
    """Recover the approval's signer; it must be the request's shopper and name
    this request. Raises BadSignature otherwise. (Charge and deadline are the
    contract's to check against the quote and the block.)"""
    from eth_account import Account

    contract = verifying_contract or checkpoint_address()
    msg = approval_message(approval)
    if "0x" + msg["requestDigest"].hex() != request_digest(request, verifying_contract=contract).lower():
        raise BadSignature("the approval is for a different request")
    try:
        signer = Account.recover_message(approval_signable(approval, contract), signature=signature)
    except Exception as exc:  # noqa: BLE001
        raise BadSignature(f"could not recover a signer from the approval: {exc}") from exc
    if signer.lower() != str(request["shopper"]).lower():
        raise BadSignature(f"the approval was not signed by the shopper ({signer})")
    return signer
