"""scripts/write_deployments.py: fills "cover", never touches "registries"."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location("write_deployments", ROOT / "scripts" / "write_deployments.py")
wd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wd)

BOND = "0x" + "b0" * 20
CHECKPOINT = "0x" + "c0" * 20
USDC = "0xFabab97dCE620294D2B0b0e46C68964e326300Ac"


def _broadcast(include_checkpoint=True):
    txs = [
        {"hash": "0x01", "transactionType": "CREATE", "contractName": "Bond", "contractAddress": BOND},
        {"hash": "0x03", "transactionType": "CALL", "contractName": "Bond", "contractAddress": BOND},
    ]
    if include_checkpoint:
        txs.insert(1, {"hash": "0x02", "transactionType": "CREATE", "contractName": "Checkpoint",
                       "contractAddress": CHECKPOINT})
    return {
        "transactions": txs,
        "receipts": [{"transactionHash": "0x01", "blockNumber": "0x10"},
                     {"transactionHash": "0x02", "blockNumber": "0x11"}],
    }


@pytest.fixture
def out_dir(tmp_path):
    for name in ("Bond", "Checkpoint"):
        d = tmp_path / f"{name}.sol"
        d.mkdir()
        (d / f"{name}.json").write_text(json.dumps({"abi": [{"type": "function", "name": f"{name}Fn"}]}))
    return tmp_path


def test_cover_section_takes_creates_and_abis(out_dir):
    cover = wd.cover_section(_broadcast(), USDC, out_dir)
    assert list(cover) == ["Checkpoint", "Bond", "USDC"]
    assert cover["Bond"]["address"].lower() == BOND
    assert cover["Checkpoint"]["block"] == 0x11 and cover["Bond"]["tx"] == "0x01"
    assert cover["Bond"]["abi"] == [{"type": "function", "name": "BondFn"}]
    assert cover["USDC"]["address"] == USDC
    names = {e["name"] for e in cover["USDC"]["abi"]}
    assert {"approve", "balanceOf", "allowance", "decimals", "Transfer"} <= names


def test_missing_checkpoint_create_stops(out_dir):
    with pytest.raises(SystemExit, match="Checkpoint"):
        wd.cover_section(_broadcast(include_checkpoint=False), USDC, out_dir)


def test_write_keeps_registries_and_other_keys(out_dir, tmp_path):
    real = json.loads((ROOT / "deployments" / "ink-sepolia.json").read_text())
    path = tmp_path / "d.json"
    path.write_text(json.dumps(real, indent=2) + "\n")
    data = wd.write(path, wd.cover_section(_broadcast(), USDC, out_dir))
    again = json.loads(path.read_text())
    assert again == data
    assert again["registries"] == real["registries"]
    assert {k: v for k, v in again.items() if k != "cover"} == {k: v for k, v in real.items() if k != "cover"}
    assert again["cover"]["Checkpoint"]["address"].lower() == CHECKPOINT
    # Francesco's runner requires address and abi on every cover entry.
    assert all(v["address"] and v["abi"] for v in again["cover"].values())


def test_write_to_out_leaves_source_alone(out_dir, tmp_path):
    src = tmp_path / "src.json"
    src.write_text(json.dumps({"registries": {"agentId": None}, "cover": {}}, indent=2) + "\n")
    before = src.read_text()
    wd.write(src, wd.cover_section(_broadcast(), USDC, out_dir), tmp_path / "out.json")
    assert src.read_text() == before
    assert json.loads((tmp_path / "out.json").read_text())["cover"]["USDC"]["address"] == USDC
