"""J3 smoke: quote the HMX Snowflake switches to Ana's address and print the Quote.

    ~/venvs/cover/bin/python scripts/pay_smoke.py                  # quote only, spends nothing
    ~/venvs/cover/bin/python scripts/pay_smoke.py --checkout       # asks you to type the total, then pays

Runs in WSL (the Kwal skill needs Linux). Reads ANA_SHIP_TO_JSON and
KWAL_CREDENTIALS from the root .env. Every raw Kwal response is saved under
service/fixtures/kwal/<run>/ with the address redacted.

`--checkout` SPENDS TEST USDC from Ana's Kwal vault (about 15.73 to a US
address). It only runs after you type the exact total, or pass the same
value as --confirm-total.
"""
from __future__ import annotations

import argparse
import dataclasses
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

from service.payments import kwal  # noqa: E402

QUERY = "HMX Snowflake"
TITLE = "HMX Snowflake Linear Switches"
SHOP = "divinikey"
CHOICES = {"size": "18 set"}


def usdc(units: int) -> str:
    return f"{units / 1_000_000:.2f}"


def find_product() -> str:
    for _ in range(3):  # Kwal search can come back empty once; the skill says retry
        for product in kwal.search(QUERY, limit=5):
            if product.title == TITLE and product.shop == SHOP:
                return product.product_id
    raise SystemExit(f"{TITLE} ({SHOP}) not found in Kwal search")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--checkout", action="store_true", help="pay the quote (spends test USDC)")
    parser.add_argument("--confirm-total", help="the exact total, e.g. 15.73, instead of typing it")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    raw = os.environ.get("ANA_SHIP_TO_JSON", "").strip()
    if not raw:
        raise SystemExit("ANA_SHIP_TO_JSON is empty in .env (US address; see JAYDON.local.md)")
    ship_to = kwal.ShipTo.from_json(raw)

    product_id = find_product()
    variant_id = kwal.variant(product_id, CHOICES)
    q = kwal.quote(variant_id, 1, ship_to)
    print("Quote")
    for name, value in dataclasses.asdict(q).items():
        print(f"  {name:17} {value}")
    print(f"  listed            ${q.listed_usd_cents / 100:.2f}   charge {usdc(q.charge_usdc)} USDC")

    state = kwal.funding(q.quote_id)
    available = state.available.minor_units if state.available else 0
    print(f"Vault {state.vault_address}: {state.state}, {usdc(available)} USDC available")
    print(f"Fixtures: {kwal._run_dir}")

    if not args.checkout:
        print("Quote only. Nothing was paid. Re-run with --checkout to pay.")
        return 0

    total = usdc(q.charge_usdc)
    typed = args.confirm_total or input(f"Pay {total} USDC from the vault for {q.title}? Type {total} to confirm: ")
    if typed.strip() != total:
        print("Not confirmed. Nothing was paid.")
        return 1
    paid = kwal.checkout(q.quote_id)
    print(f"Checkout submitted: payment {paid.payment_id}, {paid.state} ({paid.step})")
    paid = kwal.wait_for_payment(paid.payment_id, quote_id=q.quote_id)
    charged = f"{paid.charged}" if paid.charged else "n/a"
    print(f"Payment {paid.payment_id}: {paid.state}, step {paid.step}, charged {charged}")
    if paid.reason:
        print(f"Reason: {paid.reason}")
    return 0 if paid.state == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())
