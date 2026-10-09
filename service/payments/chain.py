"""web3.py calls to the deployed Checkpoint and Bond (J7).

`Chain` implements `flow.Checkpoint` (request_id, check, release, confirm)
plus the A5 route (`release_approved`) and the reads the runner and the maker
screen need. Addresses and ABIs come from `DEPLOYMENTS_FILE`
(`deployments/ink-sepolia.json`), never from code.

Transactions:
- Every send is built with `build_transaction`, which runs `eth_estimateGas`
  first, so a revert surfaces before anything is signed, as `Reverted` with
  the custom error's name (and, for a Checkpoint rule, its RULES name).
- Each sender keeps a local nonce under a lock, so `release` and `confirm`
  can go back to back without waiting for the node's pending count. A failed
  send drops the local nonce and the next one re-reads it from the node.
- Every send waits for its receipt; a receipt with status 0 is `Reverted`.

Module-level `get_limits`, `get_free_cover`, `check` and friends use one
`default()` Chain built from the environment (INK_RPC, DEPLOYMENTS_FILE,
SERVICE_PRIVATE_KEY), which is what `service/runner.py` imports.
"""
from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from service.guard import signing
from service.guard.rules import Limits

from .flow import Released

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RPC = "https://rpc-gel-sepolia.inkonchain.com"
RECEIPT_TIMEOUT = 120  # seconds; Ink Sepolia blocks are ~1 s

# Checkpoint custom error -> guard RULES name (bit order of check()).
RULE_OF_ERROR = {
    "OverRequestMax": "over_request_max",
    "OverPerItem": "over_per_item",
    "OverMonthly": "over_monthly",
    "ShopNotAllowed": "shop_not_allowed",
    "WrongAddress": "wrong_address",
    "Expired": "expired",
    "BadSignature": "bad_signature",
    "NotEnoughCover": "not_enough_cover",
    "NeedsApproval": "needs_approval",
    "NonceUsed": "nonce_used",
    "InsufficientBalance": "low_balance",
}


class ChainConfigError(RuntimeError):
    """Missing address, ABI, key or RPC."""


class Reverted(Exception):
    """A call or transaction reverted. `error` is the custom error's name when
    the ABIs know it; `rule` is the guard's RULES name for a Checkpoint rule."""

    def __init__(self, error: str, *, rule: Optional[str] = None, tx_hash: Optional[str] = None, raw: Any = None):
        super().__init__(f"reverted: {error}" + (f" ({rule})" if rule else ""))
        self.error = error
        self.rule = rule
        self.tx_hash = tx_hash
        self.raw = raw


@dataclass(frozen=True)
class Score:
    avg: int
    count: int


# ----------------------------------------------------------------- helpers


def load_deployments(path: str | Path | None = None) -> dict:
    p = Path(path or os.environ.get("DEPLOYMENTS_FILE") or "deployments/ink-sepolia.json")
    if not p.is_absolute():
        p = ROOT / p
    return json.loads(p.read_text(encoding="utf-8"))


def request_tuple(request: dict) -> tuple:
    """The PurchaseRequest struct in ABI order, coerced the same way it is signed."""
    msg = signing.message(request)
    return tuple(msg[f["name"]] for f in signing.fields())


def _bytes32(value) -> bytes:
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    return bytes.fromhex(str(value).removeprefix("0x").rjust(64, "0"))


def bought_tuple(b: dict) -> tuple:
    return (
        _bytes32(b["quoteIdHash"]),
        b["shop"],
        b["colour"],
        b["size"],
        b["model"],
        int(b["listedUsdCents"]),
        int(b["chargeUsdc"]),
    )


def approval_tuple(a: dict) -> tuple:
    return (_bytes32(a["requestDigest"]), int(a["chargeUsdc"]), int(a["deadline"]))


def _sig(signature) -> bytes:
    if isinstance(signature, (bytes, bytearray)):
        return bytes(signature)
    return bytes.fromhex(str(signature).removeprefix("0x"))


def _hex(value) -> str:
    h = value.hex() if hasattr(value, "hex") else str(value)
    return h if h.startswith("0x") else "0x" + h


def error_selectors(abis: dict[str, list]) -> dict[str, tuple[str, str]]:
    """4-byte selector -> (contract, error name), over every error in the ABIs."""
    from eth_utils import keccak

    out: dict[str, tuple[str, str]] = {}
    for contract, abi in abis.items():
        for item in abi:
            if item.get("type") != "error":
                continue
            types = ",".join(_abi_type(i) for i in item.get("inputs", []))
            sel = "0x" + keccak(text=f"{item['name']}({types})")[:4].hex()
            out.setdefault(sel, (contract, item["name"]))
    return out


def _abi_type(i: dict) -> str:
    t = i["type"]
    if t.startswith("tuple"):
        return "(" + ",".join(_abi_type(c) for c in i["components"]) + ")" + t[len("tuple"):]
    return t


class _Sender:
    """One key: a lock and a local nonce."""

    def __init__(self, w3, key: str):
        from eth_account import Account

        self.account = Account.from_key(key)
        self.address = self.account.address
        self.lock = threading.Lock()
        self._w3 = w3
        self._nonce: Optional[int] = None

    def next_nonce(self) -> int:
        if self._nonce is None:
            self._nonce = self._w3.eth.get_transaction_count(self.address, "pending")
        n = self._nonce
        self._nonce += 1
        return n

    def reset(self) -> None:
        self._nonce = None


# -------------------------------------------------------------------- Chain


class Chain:
    """The deployed Cover contracts, read with any RPC and written with the service key."""

    def __init__(self, w3, deployments: dict, service_key: Optional[str] = None):
        self.w3 = w3
        self.deployments = deployments
        self.contracts: dict[str, Any] = {}
        abis: dict[str, list] = {}
        for section in ("cover", "registries"):
            for name, entry in (deployments.get(section) or {}).items():
                if isinstance(entry, dict) and entry.get("address") and entry.get("abi"):
                    self.contracts[name] = w3.eth.contract(address=w3.to_checksum_address(entry["address"]), abi=entry["abi"])
                    abis[name] = entry["abi"]
        for name in ("Checkpoint", "Bond"):
            if name not in self.contracts:
                raise ChainConfigError(f"no {name} address/ABI in the deployments file")
        self.checkpoint = self.contracts["Checkpoint"]
        self.bond = self.contracts["Bond"]
        self._errors = error_selectors(abis)
        self._senders: dict[str, _Sender] = {}
        self._senders_lock = threading.Lock()
        self.service = self.sender(service_key) if service_key else None

    @classmethod
    def from_env(cls, *, deployments_file: str | None = None, rpc: str | None = None, service_key: str | None = None) -> "Chain":
        from web3 import Web3

        url = rpc or os.environ.get("INK_RPC") or DEFAULT_RPC
        w3 = Web3(Web3.HTTPProvider(url, request_kwargs={"timeout": 30}))
        key = service_key if service_key is not None else os.environ.get("SERVICE_PRIVATE_KEY") or None
        return cls(w3, load_deployments(deployments_file), key)

    @property
    def checkpoint_address(self) -> str:
        return self.checkpoint.address

    # ------------------------------------------------------------ plumbing

    def sender(self, key: str) -> _Sender:
        from eth_account import Account

        address = Account.from_key(key).address
        with self._senders_lock:
            if address not in self._senders:
                self._senders[address] = _Sender(self.w3, key)
            return self._senders[address]

    def decode_revert(self, exc: Exception) -> Optional[Reverted]:
        """A Reverted for a web3 revert exception, or None if it isn't one."""
        from web3.exceptions import ContractCustomError, ContractLogicError

        if not isinstance(exc, (ContractCustomError, ContractLogicError)):
            return None
        data = getattr(exc, "data", None)
        if isinstance(data, (bytes, bytearray)):
            data = "0x" + bytes(data).hex()
        if isinstance(data, str) and data.startswith("0x") and len(data) >= 10:
            hit = self._errors.get(data[:10].lower())
            if hit:
                contract, name = hit
                rule = RULE_OF_ERROR.get(name) if contract in ("Checkpoint", "Bond") else None
                return Reverted(name, rule=rule, raw=data)
            return Reverted(f"unknown error {data[:10]}", raw=data)
        return Reverted(getattr(exc, "message", None) or str(exc), raw=data)

    def call(self, contract: str, fn: str, *args):
        try:
            return self.contracts[contract].functions[fn](*args).call()
        except Exception as exc:  # noqa: BLE001 - rethrown decoded or as is
            decoded = self.decode_revert(exc)
            if decoded:
                raise decoded from exc
            raise

    def send(self, sender: _Sender, contract: str, fn: str, *args, gas: Optional[int] = None):
        """Build (estimating gas, so reverts surface here), sign, send and wait.
        Returns the receipt; raises Reverted on a revert at either stage."""
        function = self.contracts[contract].functions[fn](*args)
        with sender.lock:
            params: dict[str, Any] = {"from": sender.address, "chainId": self.w3.eth.chain_id}
            if gas:
                params["gas"] = gas
            try:
                params["nonce"] = sender.next_nonce()
                tx = function.build_transaction(params)
                signed = sender.account.sign_transaction(tx)
                tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            except Exception as exc:  # noqa: BLE001
                sender.reset()
                decoded = self.decode_revert(exc)
                if decoded:
                    raise decoded from exc
                raise
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=RECEIPT_TIMEOUT)
        if receipt["status"] != 1:
            raise Reverted(f"{contract}.{fn} reverted onchain", tx_hash=_hex(tx_hash))
        return receipt

    def _service(self) -> _Sender:
        if self.service is None:
            raise ChainConfigError("SERVICE_PRIVATE_KEY is not set; the service cannot release or confirm")
        return self.service

    # ------------------------------------------------ flow.Checkpoint (pay)

    def request_id(self, request: dict) -> str:
        """`Checkpoint.hashRequest(r)`, computed locally (same bytes, no RPC)."""
        return signing.request_digest(request, verifying_contract=self.checkpoint_address)

    def check(self, request: dict, signature: str, bought: dict) -> int:
        return int(self.call("Checkpoint", "check", request_tuple(request), _sig(signature), bought_tuple(bought)))

    def release(self, request: dict, signature: str, bought: dict) -> Released:
        receipt = self.send(
            self._service(), "Checkpoint", "release", request_tuple(request), _sig(signature), bought_tuple(bought)
        )
        return self._released(receipt)

    def release_approved(
        self, request: dict, signature: str, approval: dict, approval_sig: str, bought: dict
    ) -> Released:
        """A5: `releaseApproved`. Not covered, so no Bond reserve and no fee."""
        receipt = self.send(
            self._service(),
            "Checkpoint",
            "releaseApproved",
            request_tuple(request),
            _sig(signature),
            approval_tuple(approval),
            _sig(approval_sig),
            bought_tuple(bought),
        )
        return self._released(receipt)

    def confirm(self, purchase_id: int, payment_id_hash: str, status: int) -> str:
        receipt = self.send(self._service(), "Checkpoint", "confirm", int(purchase_id), _bytes32(payment_id_hash), int(status))
        return _hex(receipt["transactionHash"])

    def _released(self, receipt) -> Released:
        from web3.logs import DISCARD

        recorded = self.checkpoint.events.PurchaseRecorded().process_receipt(receipt, errors=DISCARD)
        if not recorded:
            raise Reverted("no PurchaseRecorded in the release receipt", tx_hash=_hex(receipt["transactionHash"]))
        pid = int(recorded[0]["args"]["purchaseId"])
        reserved = self.bond.events.Reserved().process_receipt(receipt, errors=DISCARD)
        fee = next((int(e["args"]["feeUsdc"]) for e in reserved if int(e["args"]["purchaseId"]) == pid), 0)
        return Released(purchase_id=pid, tx_hash=_hex(receipt["transactionHash"]), fee_usdc=fee)

    # ---------------------------------------------------------------- reads

    def get_limits(self, shopper: str) -> Limits:
        per_item, monthly, shops, address_hash, ends_at, spent = self.call(
            "Checkpoint", "limitsOf", self.w3.to_checksum_address(shopper)
        )
        return Limits(
            per_item_max_cents=int(per_item),
            monthly_max_cents=int(monthly),
            shops=list(shops),
            address_hash=_hex(address_hash),
            ends_at=int(ends_at),
            spent_this_month_cents=int(spent),
        )

    def get_free_cover(self, agent_id) -> int:
        return int(self.call("Bond", "freeCover", int(agent_id)))

    def score(self, agent_id) -> Score:
        avg, count = self.call("Bond", "score", int(agent_id))
        return Score(int(avg), int(count))

    def fee_bps(self, agent_id) -> int:
        return int(self.call("Bond", "feeBps", int(agent_id)))

    def auto_pay_limit_cents(self, agent_id, shopper: str) -> int:
        return int(self.call("Checkpoint", "autoPayLimitCents", int(agent_id), self.w3.to_checksum_address(shopper)))

    def balance_of(self, shopper: str) -> int:
        """Ana's USDC held by the Checkpoint (6 decimals)."""
        return int(self.call("Checkpoint", "balanceOf", self.w3.to_checksum_address(shopper)))

    def nonce_used(self, shopper: str, nonce) -> bool:
        return bool(self.call("Checkpoint", "nonceUsed", self.w3.to_checksum_address(shopper), int(nonce)))

    def maker(self, agent_id) -> dict:
        """Everything the maker screen shows, in one place."""
        a = int(agent_id)
        s = self.score(a)
        return {
            "agent_id": str(a),
            "deposited": int(self.call("Bond", "deposited", a)),
            "reserved": int(self.call("Bond", "reserved", a)),
            "free_cover": self.get_free_cover(a),
            "claims_paid": int(self.call("Bond", "claimsPaid", a)),
            "fees_paid": int(self.call("Bond", "feesPaid", a)),
            "score_average": s.avg,
            "score_count": s.count,
            "fee_bps": self.fee_bps(a),
        }

    def bond_purchase(self, purchase_id) -> dict:
        p = self.call("Bond", "purchase", int(purchase_id))
        names = ("agentId", "shopper", "chargeUsdc", "feeUsdc", "askedHash", "boughtHash", "reservedAt", "status")
        return dict(zip(names, p))


# ------------------------------------------------------ module-level default

_default: Optional[Chain] = None
_default_lock = threading.Lock()


def default() -> Chain:
    """The Chain from the environment, built once per process."""
    global _default
    with _default_lock:
        if _default is None:
            _default = Chain.from_env()
        return _default


def use(chain: Optional[Chain]) -> None:
    """Replace the default (tests, demo_reset against anvil)."""
    global _default
    with _default_lock:
        _default = chain


def get_limits(shopper: str) -> Limits:
    return default().get_limits(shopper)


def get_free_cover(agent_id) -> int:
    return default().get_free_cover(agent_id)


def get_fee_bps(agent_id) -> int:
    return default().fee_bps(agent_id)


def get_auto_pay_limit_cents(agent_id, shopper: str) -> int:
    return default().auto_pay_limit_cents(agent_id, shopper)


def get_maker(agent_id) -> dict:
    return default().maker(agent_id)
