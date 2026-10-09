"""Keep the bootstrap data aligned with the signed-request build plan."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_purchase_request_fields_match_the_interface() -> None:
    request = json.loads((ROOT / "shared/purchase-request.json").read_text())
    deployments = json.loads((ROOT / "deployments/ink-sepolia.json").read_text())
    assert request["primaryType"] == "PurchaseRequest"
    assert request["domain"]["name"] == "Cover"
    assert request["domain"]["version"] == "1"
    assert request["domain"]["chainId"] == deployments["chainId"] == 763373
    assert request["types"]["PurchaseRequest"] == [
        {"name": name, "type": field_type}
        for name, field_type in [
            ("shopper", "address"),
            ("agentId", "uint256"),
            ("shop", "string"),
            ("item", "string"),
            ("colour", "string"),
            ("size", "string"),
            ("model", "string"),
            ("maxUsdCents", "uint256"),
            ("addressHash", "bytes32"),
            ("nonce", "uint256"),
            ("deadline", "uint256"),
        ]
    ]


def test_deployment_sections_exist() -> None:
    deployments = json.loads((ROOT / "deployments/ink-sepolia.json").read_text())
    assert {"Identity", "Reputation", "agentId"} <= deployments["registries"].keys()
    assert {"Checkpoint", "Bond", "USDC"} <= deployments["cover"].keys()
    for section, names in [
        ("registries", ["Identity", "Reputation"]),
        ("cover", ["Checkpoint", "Bond", "USDC"]),
    ]:
        for name in names:
            contract = deployments[section][name]
            assert "address" in contract
            assert isinstance(contract["abi"], list)
