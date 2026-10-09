"""Mutation check for Checkpoint.sol and Bond.sol: each mutant must fail `forge test`.

Run in WSL: python contracts/test/mutate.py ["mutant name" ...]. Restores every file it touches.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORGE = str(Path.home() / ".foundry/bin/forge")
CP, BOND = ROOT / "src/Checkpoint.sol", ROOT / "src/Bond.sol"

MUTANTS = [
    # Checkpoint: the rules
    ("cp per-item cap inclusive -> off by one", CP, "amount > l.perItemMaxCents)", "amount > l.perItemMaxCents + 1)"),
    ("cp unset per-item allows", CP, "l.perItemMaxCents == 0 || ", ""),
    ("cp unset monthly allows", CP, "l.monthlyMaxCents == 0 || ", ""),
    ("cp signed max off by one", CP, "amount > r.maxUsdCents)", "amount > r.maxUsdCents + 1)"),
    ("cp zero signed max allows", CP, "r.maxUsdCents == 0 || ", ""),
    ("cp monthly ignores prior spend", CP, "spentCents[r.shopper][currentPeriod()] + amount > l.monthlyMaxCents", "amount > l.monthlyMaxCents"),
    ("cp signed shop not binding", CP, "if (bytes(signedShop).length != 0 && keccak256(_lower(signedShop)) != boughtKey) return false;", ""),
    ("cp shop list ignored", CP, "if (keccak256(bytes(shops[i])) == boughtKey) return true;", "return true;"),
    ("cp address unchecked", CP, "r.addressHash != l.addressHash", "false"),
    ("cp unset address allows", CP, "l.addressHash == bytes32(0) || ", ""),
    ("cp deadline inclusive", CP, "block.timestamp >= r.deadline", "block.timestamp > r.deadline"),
    ("cp limits end ignored", CP, " || block.timestamp >= l.endsAt", ""),
    ("cp signature unchecked", CP, "_recover(hashRequest(r), sig) != r.shopper", "false"),
    ("cp high-s accepted", CP, "if (uint256(s) > HALF_N) return address(0);", ""),
    ("cp cover unchecked", CP, "if (b.chargeUsdc + fee > bond.freeCover(r.agentId)) mask |= NOT_ENOUGH_COVER;", ""),
    ("cp band unchecked", CP, "if (amount > autoPayLimitCents(r.agentId, r.shopper)) mask |= NEEDS_APPROVAL;", ""),
    ("cp mid band = high band", CP, "if (avg >= midBand) return midCapCents;", "if (avg >= midBand) return _limits[shopper].perItemMaxCents;"),
    ("cp nonce not marked", CP, "nonceUsed[r.shopper][r.nonce] = true;", ""),
    ("cp nonce not checked", CP, "if (nonceUsed[r.shopper][r.nonce]) mask |= NONCE_USED;", ""),
    ("cp balance unchecked", CP, "if (balanceOf[r.shopper] < b.chargeUsdc) mask |= LOW_BALANCE;", ""),
    ("cp release open to anyone", CP, "if (msg.sender != service) revert NotService();\n        _revertFirst(_failed(r, sig, b, true));", "_revertFirst(_failed(r, sig, b, true));"),
    ("cp charge ignored in amount", CP, "return listedUsdCents > chargeCents ? listedUsdCents : chargeCents;", "return listedUsdCents;"),
    ("cp approval digest unchecked", CP, "a.requestDigest != hashRequest(r) || ", ""),
    ("cp approval amount unchecked", CP, "a.chargeUsdc != b.chargeUsdc || ", ""),
    ("cp approval signer unchecked", CP, "\n                || _recover(hashApproval(a), approvalSig) != r.shopper", ""),
    ("cp spend not recorded", CP, "spentCents[r.shopper][period] += amount;", ""),
    ("cp 'any' not filled from bought", CP, "return bytes(asked).length == 0 ? bought : asked;", "return asked;"),
    # Bond
    ("bond reserve open to anyone", BOND, "if (msg.sender != checkpoint) revert NotCheckpoint();\n        if (_purchases[purchaseId].status != Status.None)", "if (_purchases[purchaseId].status != Status.None)"),
    ("bond over-reserve allowed", BOND, "if (chargeUsdc + fee > freeCover(agentId)) revert NotEnoughCover();", ""),
    ("bond reserved not held", BOND, "uint256 held = reserved[agentId] + pendingWithdrawal[agentId].amount;", "uint256 held = pendingWithdrawal[agentId].amount;"),
    ("bond pending not held", BOND, "uint256 held = reserved[agentId] + pendingWithdrawal[agentId].amount;", "uint256 held = reserved[agentId];"),
    ("bond withdraw delay skipped", BOND, "if (block.timestamp < w.unlockAt) revert TooEarly();", ""),
    ("bond deposit/withdraw not owner-only", BOND, "if (identity.ownerOf(agentId) != msg.sender) revert NotOwner();", ""),
    ("bond claim by anyone", BOND, "if (msg.sender != p.shopper) revert NotShopper();", ""),
    ("bond claim after window", BOND, "if (block.timestamp >= p.reservedAt + claimWindow) revert WindowClosed();", ""),
    ("bond release inside window", BOND, "if (block.timestamp < p.reservedAt + claimWindow) revert WindowOpen();", ""),
    ("bond every claim refunds", BOND, "bool mismatch = p.askedHash != p.boughtHash;", "bool mismatch = true;"),
    ("bond no claim refunds", BOND, "bool mismatch = p.askedHash != p.boughtHash;", "bool mismatch = false;"),
    ("bond release twice", BOND, "if (p.status != Status.Reserved) revert WrongStatus();\n        if (block.timestamp < p.reservedAt", "if (block.timestamp < p.reservedAt"),
    ("bond judge open to anyone", BOND, "if (msg.sender != judge) revert NotJudge();", ""),
    ("bond flat fee", BOND, "BASE_FEE_BPS + FEE_BPS_PER_POINT * (100 - avg)", "BASE_FEE_BPS"),
    ("bond fee not to treasury", BOND, "if (fee > 0 && !usdc.transfer(treasury, fee)) revert TransferFailed();", ""),
    ("bond score write not caught", BOND, "try reputation.giveFeedback(", "reputation.giveFeedback("),
    ("bond trusts short registry count", BOND, "if (n == total && decimals <= 18)", "if (decimals <= 18)"),
    ("bond refund doesn't debit deposit", BOND, "deposited[p.agentId] -= p.chargeUsdc;\n        claimsPaid", "claimsPaid"),
    ("bond review skips maker owner check", BOND, "_onlyOwner(p.agentId);\n        if (p.status != Status.NeedsReview)", "if (p.status != Status.NeedsReview)"),
]

# "score write not caught" leaves a dangling `) { written = true; } catch {}`; patch it to compile.
FIXUPS = {
    "bond score write not caught": (") {\n                written = true;\n            } catch {}", ");\n            written = true;"),
}


ONLY = set(sys.argv[1:])


def run() -> int:
    survived = []
    for name, path, old, new in [m for m in MUTANTS if not ONLY or m[0] in ONLY]:
        original = path.read_text()
        if original.count(old) != 1:
            print(f"SKIP  {name}: pattern found {original.count(old)} times")
            survived.append(name + " (pattern)")
            continue
        mutated = original.replace(old, new)
        if name in FIXUPS:
            a, b = FIXUPS[name]
            assert mutated.count(a) == 1, name
            mutated = mutated.replace(a, b)
        try:
            path.write_text(mutated)
            res = subprocess.run([FORGE, "test"], cwd=ROOT, capture_output=True, text=True)
        finally:
            path.write_text(original)
        out = res.stdout + res.stderr
        if "Compiler run failed" in out or "Error (" in out:
            print(f"BUILD {name}")
            survived.append(name + " (did not compile)")
        elif res.returncode == 0:
            print(f"ALIVE {name}")
            survived.append(name)
        else:
            failed = [l.strip() for l in out.splitlines() if l.startswith("[FAIL")]
            print(f"KILL  {name}: {len(set(failed))} failing, e.g. {failed[0][:100] if failed else '?'}")
    print(f"\n{len(ONLY or MUTANTS) - len(survived)}/{len(ONLY or MUTANTS)} killed")
    for s in survived:
        print("  survived:", s)
    return 1 if survived else 0


if __name__ == "__main__":
    sys.exit(run())
