"""chain.py against the real compiled Checkpoint and Bond on a local anvil.

Covers J7 (check, release, confirm through pay()), the wrong-item refund,
A2b (a claim on the item Ana asked for is rejected), the refusal beat
(amount + shop + address together), and A5 (score drops, NeedsApproval,
pay_approved through releaseApproved). Kwal is a fake; no network.

Skips unless `anvil` is on PATH (or ~/.foundry/bin) and `contracts/out` is built.
"""
from __future__ import annotations

import asyncio
import json
import shutil
import socket
import subprocess
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "contracts" / "out"
ANVIL = shutil.which("anvil") or str(Path.home() / ".foundry" / "bin" / "anvil")

pytestmark = pytest.mark.skipif(
    not (Path(ANVIL).exists() and (OUT / "Checkpoint.sol" / "Checkpoint.json").exists()),
    reason="needs anvil and forge build output",
)

# anvil's well-known dev keys (test only)
KEYS = [
    "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",  # deployer
    "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d",  # service
    "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a",  # ana
    "0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6",  # maker
    "0x47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a",  # judge
]
SHOP = "forza sports"
ADDRESS_HASH = "0x" + "ab" * 32
CHARGE = 21_710_000  # SISU to a US address
LISTED = 1_999


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _artifact(sol: str, name: str):
    data = json.loads((OUT / sol / f"{name}.json").read_text())
    return data["abi"], data["bytecode"]["object"]


@pytest.fixture(scope="module")
def env():
    from eth_account import Account
    from web3 import Web3

    port = _free_port()
    proc = subprocess.Popen(
        [ANVIL, "--port", str(port), "--chain-id", "763373", "--silent"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    w3 = Web3(Web3.HTTPProvider(f"http://127.0.0.1:{port}"))
    for _ in range(100):
        try:
            if w3.is_connected():
                break
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.1)
    deployer, service, ana, maker, judge = (Account.from_key(k) for k in KEYS)

    def tx(acct, fn):
        built = fn.build_transaction({"from": acct.address, "nonce": w3.eth.get_transaction_count(acct.address)})
        h = w3.eth.send_raw_transaction(acct.sign_transaction(built).raw_transaction)
        r = w3.eth.wait_for_transaction_receipt(h)
        assert r["status"] == 1
        return r

    def deploy(sol, name, *args):
        abi, code = _artifact(sol, name)
        r = tx(deployer, w3.eth.contract(abi=abi, bytecode=code).constructor(*args))
        return w3.eth.contract(address=r["contractAddress"], abi=abi)

    usdc = deploy("Mocks.sol", "MockUSDC")
    identity = deploy("Mocks.sol", "MockIdentity")
    reputation = deploy("Mocks.sol", "MockReputation", identity.address)
    treasury = Account.create().address
    vault = Account.create().address
    bond = deploy("Bond.sol", "Bond", usdc.address, identity.address, reputation.address, treasury, judge.address, 600, 600)
    checkpoint = deploy("Checkpoint.sol", "Checkpoint", usdc.address, bond.address, vault, service.address, 90, 60, 5000)
    tx(deployer, bond.functions.setCheckpoint(checkpoint.address))
    tx(deployer, identity.functions.register(maker.address))
    agent_id = 1

    tx(deployer, usdc.functions.mint(maker.address, 200_000_000))
    tx(deployer, usdc.functions.mint(ana.address, 200_000_000))
    tx(maker, usdc.functions.approve(bond.address, 2**255))
    tx(maker, bond.functions.deposit(agent_id, 100_000_000))
    tx(ana, usdc.functions.approve(checkpoint.address, 2**255))
    tx(ana, checkpoint.functions.deposit(150_000_000))
    ends = w3.eth.get_block("latest")["timestamp"] + 30 * 86400
    tx(ana, checkpoint.functions.setLimits(10_000, 30_000, [SHOP], bytes.fromhex(ADDRESS_HASH[2:]), ends))

    from service.payments.chain import Chain

    deployments = {
        "cover": {
            "Checkpoint": {"address": checkpoint.address, "abi": checkpoint.abi},
            "Bond": {"address": bond.address, "abi": bond.abi},
            "USDC": {"address": usdc.address, "abi": usdc.abi},
        }
    }
    chain = Chain(w3, deployments, KEYS[1])
    yield SimpleNamespace(w3=w3, chain=chain, ana=ana, maker=maker, agent_id=agent_id, usdc=usdc,
                          bond=bond, checkpoint=checkpoint, vault=vault, treasury=treasury, tx=tx)
    proc.terminate()
    proc.wait(timeout=10)


_nonce = iter(range(1, 10_000))


def request(env, **over):
    deadline = env.w3.eth.get_block("latest")["timestamp"] + 3600
    r = dict(shopper=env.ana.address, agentId=env.agent_id, shop=SHOP, item="SISU Large Aero Guard 2.0mm",
             colour="charcoal black", size="", model="", maxUsdCents=2_500, addressHash=ADDRESS_HASH,
             nonce=next(_nonce), deadline=deadline)
    r.update(over)
    return r


def sign(env, r):
    from service.guard import sign_request

    return sign_request(r, env.ana.key.hex(), verifying_contract=env.chain.checkpoint_address)


def quote(colour="snow white", charge=CHARGE, listed=LISTED, shop=SHOP, qid=None):
    from service.payments.kwal import Quote

    return Quote(quote_id=qid or f"q-{time.time_ns()}", product_id="prd", variant_id="var", shop=shop,
                 title="SISU Large Aero Guard 2.0mm", colour=colour, size="", model="", image_url=None,
                 listed_usd_cents=listed, charge_usdc=charge, sandbox_pricing=False)


class FakeKwal:
    def wait_for_funding(self, quote_id, timeout):
        return SimpleNamespace(state="ready")

    def checkout(self, quote_id):
        return SimpleNamespace(payment_id=f"pay_{quote_id}")

    def wait_for_payment(self, payment_id, timeout, *, quote_id=None):
        return SimpleNamespace(state="completed")


def collect(gen):
    async def go():
        out = []
        try:
            async for e in gen:
                out.append(e)
        except Exception as exc:  # noqa: BLE001
            return out, exc
        return out, None

    return asyncio.run(go())


def test_request_id_matches_hash_request(env):
    from service.payments.chain import request_tuple

    r = request(env)
    onchain = env.checkpoint.functions.hashRequest(request_tuple(r)).call()
    assert env.chain.request_id(r) == "0x" + onchain.hex()


def test_limits_and_cover_reads(env):
    limits = env.chain.get_limits(env.ana.address)
    assert limits.per_item_max_cents == 10_000 and limits.shops == [SHOP]
    assert limits.address_hash == ADDRESS_HASH
    assert env.chain.get_free_cover(env.agent_id) == 100_000_000
    assert env.chain.score(env.agent_id).avg == 100 and env.chain.fee_bps(env.agent_id) == 50


def test_refusal_beat_reports_amount_shop_address_and_release_reverts_by_name(env):
    from service.payments import flow
    from service.payments.chain import Reverted

    r = request(env, maxUsdCents=100, shop="gmktec", addressHash="0x" + "cd" * 32)
    sig = sign(env, r)
    q = quote(shop="gmktec", listed=679_900, charge=6_799_000_000)
    names = flow.from_bitmask(env.chain.check(r, sig, flow.bought(q)))
    assert {"over_request_max", "shop_not_allowed", "wrong_address"} <= set(names)
    with pytest.raises(Reverted) as e:
        env.chain.release(r, sig, flow.bought(q))
    assert e.value.error == "OverRequestMax" and e.value.rule == "over_request_max"
    events, exc = collect(flow.pay(r, sig, q, chain=env.chain, kwal=FakeKwal()))
    assert exc is None and [x.step for x in events] == ["refused"]
    assert "amount" in events[0].detail and "shop" in events[0].detail and "address" in events[0].detail


def test_covered_purchase_then_wrong_item_refund_then_a2b_rejection(env):
    from service.payments import flow

    before_vault = env.usdc.functions.balanceOf(env.vault).call()
    r = request(env)
    events, exc = collect(flow.pay(r, sign(env, r), quote(), chain=env.chain, kwal=FakeKwal()))
    assert exc is None, exc
    assert [e.step for e in events] == ["checked", "released", "fee_taken", "funded", "funded", "paid", "paid", "confirmed"]
    pid = events[1].purchase_id
    assert pid >= 1 and events[0].purchase_id == 0
    assert "0.11 USDC" in events[2].detail  # 0.5% of 21.71
    assert env.usdc.functions.balanceOf(env.vault).call() == before_vault + CHARGE
    assert env.checkpoint.functions.purchase(pid).call()[7] == 1  # status PAID
    assert env.bond.functions.reserved(env.agent_id).call() == CHARGE

    # Wrong item: Ana asked charcoal black, got snow white -> refunded from the deposit.
    ana_before = env.usdc.functions.balanceOf(env.ana.address).call()
    env.tx(env.ana, env.bond.functions.openClaim(pid))
    assert env.usdc.functions.balanceOf(env.ana.address).call() == ana_before + CHARGE
    assert env.chain.bond_purchase(pid)["status"] == 3  # Refunded
    assert env.chain.score(env.agent_id).avg == 0

    # A2b: she asked for exactly what arrived -> the claim is rejected, no money moves.
    r2 = request(env, colour="snow white")
    events, exc = collect(flow.pay(r2, sign(env, r2), quote(), chain=env.chain, kwal=FakeKwal()))
    # score 0 now: below the 60 band, so this parks for approval instead.
    assert isinstance(exc, flow.NeedsApproval) and events[-1].step == "needs_approval"


def test_a2b_match_claim_rejected_on_a_fresh_agent(env):
    from service.payments import flow

    # Fresh agent so the score is 100 again.
    identity_addr = env.bond.functions.identity().call()
    abi, _ = _artifact("Mocks.sol", "MockIdentity")
    identity = env.w3.eth.contract(address=identity_addr, abi=abi)
    env.tx(env.maker, identity.functions.register(env.maker.address))
    agent2 = identity.functions.lastId().call()
    env.tx(env.maker, env.bond.functions.deposit(agent2, 50_000_000))

    r = request(env, agentId=agent2, colour="snow white")
    events, exc = collect(flow.pay(r, sign(env, r), quote(), chain=env.chain, kwal=FakeKwal()))
    assert exc is None, exc
    pid = events[1].purchase_id
    ana_before = env.usdc.functions.balanceOf(env.ana.address).call()
    env.tx(env.ana, env.bond.functions.openClaim(pid))
    assert env.usdc.functions.balanceOf(env.ana.address).call() == ana_before  # nothing paid
    assert env.chain.bond_purchase(pid)["status"] == 4  # Rejected
    assert env.chain.score(agent2).avg == 100


def test_a5_needs_approval_then_pay_approved(env):
    from service.guard import make_approval, sign_approval
    from service.payments import flow

    assert env.chain.score(env.agent_id).avg < 60  # after the refund above
    r = request(env)
    sig = sign(env, r)
    q = quote()
    events, exc = collect(flow.pay(r, sig, q, chain=env.chain, kwal=FakeKwal()))
    assert isinstance(exc, flow.NeedsApproval) and [e.step for e in events] == ["needs_approval"]

    deadline = env.w3.eth.get_block("latest")["timestamp"] + 600
    approval = make_approval(r, q.charge_usdc, deadline, verifying_contract=env.chain.checkpoint_address)
    asig = sign_approval(approval, env.ana.key.hex(), verifying_contract=env.chain.checkpoint_address)
    reserved_before = env.bond.functions.reserved(env.agent_id).call()
    events, exc = collect(flow.pay_approved(r, sig, approval, asig, q, chain=env.chain, kwal=FakeKwal()))
    assert exc is None, exc
    assert [e.step for e in events] == ["released", "funded", "funded", "paid", "paid", "confirmed"]
    pid = events[0].purchase_id
    assert env.checkpoint.functions.purchase(pid).call()[8] is False  # not covered
    assert env.bond.functions.reserved(env.agent_id).call() == reserved_before

    # Replaying the same approval: the request nonce is spent.
    events, exc = collect(flow.pay_approved(r, sig, approval, asig, q, chain=env.chain, kwal=FakeKwal()))
    assert exc is None and events[-1].step == "refused" and "already used" in events[-1].detail


def test_a5_approval_signed_by_someone_else_is_refused(env):
    from eth_account import Account

    from service.guard import make_approval, sign_approval
    from service.payments import flow

    r = request(env)
    sig = sign(env, r)
    q = quote()
    deadline = env.w3.eth.get_block("latest")["timestamp"] + 600
    approval = make_approval(r, q.charge_usdc, deadline, verifying_contract=env.chain.checkpoint_address)
    asig = sign_approval(approval, Account.create().key.hex(), verifying_contract=env.chain.checkpoint_address)
    events, exc = collect(flow.pay_approved(r, sig, approval, asig, q, chain=env.chain, kwal=FakeKwal()))
    assert exc is None and events[-1].step == "refused"
