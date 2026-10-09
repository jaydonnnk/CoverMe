"""J6: fill deployments/ink-sepolia.json "cover" after Deploy.s.sol broadcasts.

    python scripts/write_deployments.py                    # chain 763373, the real deploy
    python scripts/write_deployments.py --chain-id 31337 --out /tmp/anvil.json   # an anvil dry run

Reads the Bond and Checkpoint addresses from
contracts/broadcast/Deploy.s.sol/<chain>/run-latest.json, their ABIs from
contracts/out/, and USDC from USDC_ADDRESS (or --usdc). Writes only "cover";
"registries" (Francesco's) and every other key are left exactly as they were.
Each entry is {address, abi, tx, block}; USDC gets a minimal ERC-20 ABI.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"

ERC20_ABI = [
    {"type": "function", "name": "name", "stateMutability": "view", "inputs": [],
     "outputs": [{"name": "", "type": "string"}]},
    {"type": "function", "name": "symbol", "stateMutability": "view", "inputs": [],
     "outputs": [{"name": "", "type": "string"}]},
    {"type": "function", "name": "decimals", "stateMutability": "view", "inputs": [],
     "outputs": [{"name": "", "type": "uint8"}]},
    {"type": "function", "name": "balanceOf", "stateMutability": "view",
     "inputs": [{"name": "account", "type": "address"}], "outputs": [{"name": "", "type": "uint256"}]},
    {"type": "function", "name": "allowance", "stateMutability": "view",
     "inputs": [{"name": "owner", "type": "address"}, {"name": "spender", "type": "address"}],
     "outputs": [{"name": "", "type": "uint256"}]},
    {"type": "function", "name": "approve", "stateMutability": "nonpayable",
     "inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}],
     "outputs": [{"name": "", "type": "bool"}]},
    {"type": "function", "name": "transfer", "stateMutability": "nonpayable",
     "inputs": [{"name": "to", "type": "address"}, {"name": "amount", "type": "uint256"}],
     "outputs": [{"name": "", "type": "bool"}]},
    {"type": "function", "name": "transferFrom", "stateMutability": "nonpayable",
     "inputs": [{"name": "from", "type": "address"}, {"name": "to", "type": "address"},
                {"name": "amount", "type": "uint256"}],
     "outputs": [{"name": "", "type": "bool"}]},
    {"type": "event", "name": "Transfer", "anonymous": False,
     "inputs": [{"name": "from", "type": "address", "indexed": True},
                {"name": "to", "type": "address", "indexed": True},
                {"name": "value", "type": "uint256", "indexed": False}]},
    {"type": "event", "name": "Approval", "anonymous": False,
     "inputs": [{"name": "owner", "type": "address", "indexed": True},
                {"name": "spender", "type": "address", "indexed": True},
                {"name": "value", "type": "uint256", "indexed": False}]},
]


def abi_of(name: str, out_dir: Path = CONTRACTS / "out") -> list:
    path = out_dir / f"{name}.sol" / f"{name}.json"
    if not path.exists():
        raise SystemExit(f"{path} missing: run `forge build` in contracts/")
    return json.loads(path.read_text())["abi"]


def created(broadcast: dict) -> dict[str, dict]:
    """contractName -> {address, tx, block} for each CREATE in a forge broadcast."""
    blocks = {r["transactionHash"]: int(r["blockNumber"], 16) for r in broadcast.get("receipts", [])}
    found: dict[str, dict] = {}
    for tx in broadcast["transactions"]:
        if tx.get("transactionType") != "CREATE":
            continue
        found[tx["contractName"]] = {
            "address": _checksum(tx["contractAddress"]),
            "tx": tx["hash"],
            "block": blocks.get(tx["hash"]),
        }
    return found


def cover_section(broadcast: dict, usdc: str, out_dir: Path = CONTRACTS / "out") -> dict:
    made = created(broadcast)
    missing = [n for n in ("Bond", "Checkpoint") if n not in made]
    if missing:
        raise SystemExit(f"broadcast has no CREATE for {', '.join(missing)}")
    return {
        "Checkpoint": {**made["Checkpoint"], "abi": abi_of("Checkpoint", out_dir)},
        "Bond": {**made["Bond"], "abi": abi_of("Bond", out_dir)},
        "USDC": {"address": _checksum(usdc), "abi": ERC20_ABI},
    }


def write(deployments: Path, cover: dict, out: Path | None = None) -> dict:
    text = deployments.read_text()
    data = json.loads(text)
    registries = json.dumps(data.get("registries"), sort_keys=True)
    data["cover"] = {k: {"address": v["address"], "abi": v["abi"], **{x: v[x] for x in ("tx", "block") if x in v}}
                     for k, v in cover.items()}
    assert json.dumps(data.get("registries"), sort_keys=True) == registries
    (out or deployments).write_text(json.dumps(data, indent=2) + "\n")
    return data


def _checksum(address: str) -> str:
    from eth_utils import to_checksum_address

    return to_checksum_address(address)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--chain-id", type=int, default=763373)
    parser.add_argument("--deployments", type=Path, default=None, help="default: DEPLOYMENTS_FILE or deployments/ink-sepolia.json")
    parser.add_argument("--broadcast", type=Path, default=None, help="default: the chain's run-latest.json")
    parser.add_argument("--usdc", default=None, help="default: USDC_ADDRESS")
    parser.add_argument("--out", type=Path, default=None, help="write here instead of over --deployments")
    args = parser.parse_args()

    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
    except ImportError:
        pass
    deployments = args.deployments or ROOT / os.environ.get("DEPLOYMENTS_FILE", "deployments/ink-sepolia.json")
    broadcast = args.broadcast or CONTRACTS / "broadcast" / "Deploy.s.sol" / str(args.chain_id) / "run-latest.json"
    usdc = args.usdc or os.environ.get("USDC_ADDRESS")
    if not usdc:
        raise SystemExit("USDC_ADDRESS missing (env or --usdc)")
    if not broadcast.exists():
        raise SystemExit(f"{broadcast} missing: run Deploy.s.sol with --broadcast first")

    cover = cover_section(json.loads(broadcast.read_text()), usdc)
    write(deployments, cover, args.out)
    for name, entry in cover.items():
        print(f"{name:<11} {entry['address']}  ({len(entry['abi'])} ABI entries)")
    print(f"wrote cover -> {args.out or deployments}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
