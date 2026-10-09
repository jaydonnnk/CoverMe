"""Print the signature `test_eip712_matchesPythonSigner` checks.

    ~/venvs/cover/bin/python contracts/test/fixtures/python_signature.py

Signs with service/guard/signing.py, so the Foundry test proves the contract
and the guard build the same EIP-712 digest from shared/purchase-request.json.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from eth_account import Account  # noqa: E402

from service.guard.signing import sign_request  # noqa: E402

KEY = "0x" + format(0xA11CE, "064x")
CHECKPOINT = "0x" + format(0xC0FFEE, "040x")
REQUEST = {
    "shopper": Account.from_key(KEY).address,
    "agentId": 7,
    "shop": "forza sports",
    "item": "sisu aero guard",
    "colour": "charcoal black",
    "size": "",
    "model": "",
    "maxUsdCents": 2500,
    "addressHash": "0x" + "ab" * 32,
    "nonce": 42,
    "deadline": 1_791_600_600,
}

if __name__ == "__main__":
    print(sign_request(REQUEST, KEY, verifying_contract=CHECKPOINT))
