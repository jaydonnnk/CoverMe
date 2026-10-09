// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.28;

import {Bond} from "../src/Bond.sol";
import {Checkpoint} from "../src/Checkpoint.sol";
import {IBond, IERC20Min} from "../src/interfaces/ICover.sol";
import {CoverBase} from "./helpers/CoverBase.sol";

/// laeria's 19 mandate cases (service/guard/tests/test_mandate.py), onchain,
/// then the Checkpoint items of J5's "done when".
///
/// The guard's `check_rules` covers bits 0-5 only; `check()` also reports the
/// signature, cover, approval, nonce and balance. Where a laeria case asserts
/// "exactly these rules", the test masks with RULES_ONLY, as the guard would.
contract CheckpointTest is CoverBase {
    // =============================================== laeria 1-2: master switch

    function test_laeria01_autonomyOff_alwaysNeedsApproval() public {
        _history(0, 1); // score 0: auto-pay limit $0
        assertEq(checkpoint.autoPayLimitCents(agentId, ana), 0);
        assertEq(_check(_req(), _bought(100)), checkpoint.NEEDS_APPROVAL());
    }

    function test_laeria02_autonomyOff_doesNotRevert_evenWhenOverCap() public {
        _history(0, 1);
        uint256 mask = _check(_req(), _bought(1_000_000));
        assertTrue(mask & checkpoint.NEEDS_APPROVAL() != 0, "parks");
        assertTrue(mask & checkpoint.OVER_PER_ITEM() != 0, "approval doesn't lift Ana's cap");
    }

    // ===================================== laeria 3-7: unset limits must deny

    function test_laeria03_emptyMandate_deniesEverything() public {
        uint256 carolKey = 0xCA201;
        Checkpoint.PurchaseRequest memory r = _reqFor(vm.addr(carolKey)); // never called setLimits
        uint256 mask = checkpoint.check(r, _sign(carolKey, r), _bought(1));
        uint256 want = checkpoint.OVER_PER_ITEM() | checkpoint.OVER_MONTHLY() | checkpoint.SHOP_NOT_ALLOWED()
            | checkpoint.WRONG_ADDRESS() | checkpoint.EXPIRED();
        assertEq(mask & want, want);
    }

    function test_laeria04_unsetPerItem_denies() public {
        _setLimits(ana, 0, 50_000, _shops(SHOP), ADDRESS_HASH);
        assertTrue(_check(_req(), _bought(100)) & checkpoint.OVER_PER_ITEM() != 0);
    }

    function test_laeria05_unsetMonthly_denies() public {
        _setLimits(ana, 10_000, 0, _shops(SHOP), ADDRESS_HASH);
        assertTrue(_check(_req(), _bought(100)) & checkpoint.OVER_MONTHLY() != 0);
    }

    function test_laeria06_unsetAutoPayLimit_needsApproval() public {
        // No per-item cap means a top-band auto-pay limit of 0: ask Ana, never auto-pay.
        _setLimits(ana, 0, 50_000, _shops(SHOP), ADDRESS_HASH);
        assertEq(checkpoint.autoPayLimitCents(agentId, ana), 0);
        assertTrue(_check(_req(), _bought(100)) & checkpoint.NEEDS_APPROVAL() != 0);
    }

    function test_laeria07_zeroCap_isZeroAllowance() public {
        _setLimits(ana, 0, 50_000, _shops(SHOP), ADDRESS_HASH);
        assertEq(_check(_req(), _bought(1)) & RULES_ONLY, checkpoint.OVER_PER_ITEM());
    }

    function test_laeria03b_unsetLimits_denyEvenAFreeItem() public {
        // Zero amount, zero caps, zero saved address: "nothing > 0" must not read as a pass.
        _setLimits(ana, 0, 0, _shops(SHOP), bytes32(0));
        Checkpoint.PurchaseRequest memory r = _req();
        r.maxUsdCents = 0;
        r.addressHash = bytes32(0);
        uint256 want = checkpoint.OVER_REQUEST_MAX() | checkpoint.OVER_PER_ITEM() | checkpoint.OVER_MONTHLY()
            | checkpoint.WRONG_ADDRESS();
        assertEq(_check(r, _bought(0)) & RULES_ONLY, want);
    }

    // ============================================ laeria 8: per-item boundary

    function test_laeria08_perItemBoundary_inclusive() public {
        _setLimits(ana, 10_000, 10_000_000, _shops(SHOP), ADDRESS_HASH);
        assertEq(_check(_req(), _bought(9_999)), 0);
        assertEq(_check(_req(), _bought(10_000)), 0);
        assertTrue(_check(_req(), _bought(10_001)) & checkpoint.OVER_PER_ITEM() != 0);
        assertTrue(_check(_req(), _bought(1_000_000)) & checkpoint.OVER_PER_ITEM() != 0);
    }

    // ===================================== laeria 9-10: monthly counts spend

    function _spend(uint256 cents) internal {
        while (cents > 0) {
            uint256 c = cents > 10_000 ? 10_000 : cents;
            _release(_req(), _bought(c));
            cents -= c;
        }
    }

    function test_laeria09_monthlyCap_countsPriorSpend() public {
        _spend(44_900);
        assertEq(_check(_req(), _bought(5_000)), 0);
        _spend(200); // 45,100 spent
        assertEq(_check(_req(), _bought(5_000)) & RULES_ONLY, checkpoint.OVER_MONTHLY());
        (,,,,, uint256 spent) = checkpoint.limitsOf(ana);
        assertEq(spent, 45_100);
    }

    function test_laeria10_monthlyCap_exactBoundaryAllowed() public {
        _spend(45_000);
        assertEq(_check(_req(), _bought(5_000)), 0);
    }

    // ============================== laeria 11-12: the auto-pay limit parks

    function test_laeria11_aboveAutoPayLimit_parks() public {
        _history(3, 1); // score 75: the $50 band
        (uint256 avg,) = bond.score(agentId);
        assertEq(avg, 75);
        assertEq(_check(_req(), _bought(5_001)), checkpoint.NEEDS_APPROVAL());
    }

    function test_laeria12_atAutoPayLimit_executes() public {
        _history(3, 1);
        assertEq(_check(_req(), _bought(5_000)), 0);
    }

    // ===================================== laeria 13-16: categories -> shops

    function test_laeria13_shopNotInList_denies() public {
        Checkpoint.PurchaseRequest memory r = _req();
        r.shop = "";
        Checkpoint.Bought memory b = _bought(1_000);
        b.shop = "casino.example";
        assertEq(_check(r, b), checkpoint.SHOP_NOT_ALLOWED());
    }

    function test_laeria14_emptyShopList_denies() public {
        // Inverted on purpose: laeria let an empty list allow any category.
        _setLimits(ana, 10_000, 50_000, new string[](0), ADDRESS_HASH);
        assertEq(_check(_req(), _bought(1_000)), checkpoint.SHOP_NOT_ALLOWED());
    }

    function test_laeria15_signedShopBinds() public {
        _setLimits(ana, 10_000, 50_000, _shops(SHOP, "keychron.com"), ADDRESS_HASH);
        Checkpoint.Bought memory b = _bought(1_000);
        b.shop = "keychron.com"; // on her list, but she signed twelvesouth.com
        assertEq(_check(_req(), b), checkpoint.SHOP_NOT_ALLOWED());
    }

    function test_laeria16_matchingShop_passes_caseInsensitive() public {
        _setLimits(ana, 10_000, 50_000, _shops("TwelveSouth.com"), ADDRESS_HASH);
        assertEq(_check(_req(), _bought(1_000)), 0);
        (,, string[] memory shops,,,) = checkpoint.limitsOf(ana);
        assertEq(shops[0], "twelvesouth.com");
    }

    // ========================== laeria 17-19: consent binds to an amount

    function test_laeria17_priceDrift_beyondSignedMax_fails() public {
        _setLimits(ana, 100_000, 1_000_000, _shops(SHOP), ADDRESS_HASH);
        Checkpoint.PurchaseRequest memory r = _req();
        r.maxUsdCents = 5_000;
        assertEq(_check(r, _bought(40_000)), checkpoint.OVER_REQUEST_MAX());
    }

    function test_laeria18_atSignedMax_passes_oneCentOver_fails() public {
        Checkpoint.PurchaseRequest memory r = _req();
        r.maxUsdCents = 5_000;
        assertEq(_check(r, _bought(5_000)), 0);
        r = _req();
        r.maxUsdCents = 5_000;
        assertEq(_check(r, _bought(5_001)), checkpoint.OVER_REQUEST_MAX());
    }

    function test_laeria19_driftedPrice_canSatisfyStandingLimits() public {
        _setLimits(ana, 50_000, 500_000, _shops(SHOP), ADDRESS_HASH);
        assertEq(_check(_req(), _bought(40_000)), 0);
        Checkpoint.PurchaseRequest memory r = _req();
        r.maxUsdCents = 5_000;
        assertEq(_check(r, _bought(40_000)), checkpoint.OVER_REQUEST_MAX());
    }

    // ================================================ J5: every refusal

    function _expectRelease(Checkpoint.PurchaseRequest memory r, Checkpoint.Bought memory b, bytes4 err) internal {
        bytes memory sig = _sign(_keyOf(r.shopper), r);
        vm.expectRevert(err);
        vm.prank(service);
        checkpoint.release(r, sig, b);
    }

    function test_refuse_OverRequestMax() public {
        Checkpoint.PurchaseRequest memory r = _req();
        r.maxUsdCents = 2_500;
        _expectRelease(r, _bought(2_501), Checkpoint.OverRequestMax.selector);
    }

    function test_refuse_OverPerItem() public {
        _expectRelease(_req(), _bought(10_001), Checkpoint.OverPerItem.selector);
    }

    function test_refuse_OverMonthly() public {
        _setLimits(ana, 10_000, 5_000, _shops(SHOP), ADDRESS_HASH);
        _expectRelease(_req(), _bought(6_000), Checkpoint.OverMonthly.selector);
    }

    function test_refuse_ShopNotAllowed() public {
        Checkpoint.Bought memory b = _bought(1_000);
        b.shop = "gmktec";
        _expectRelease(_req(), b, Checkpoint.ShopNotAllowed.selector);
    }

    function test_refuse_WrongAddress() public {
        Checkpoint.PurchaseRequest memory r = _req();
        r.addressHash = keccak256("a new address the agent made up");
        _expectRelease(r, _bought(1_000), Checkpoint.WrongAddress.selector);
    }

    function test_refuse_Expired_deadline() public {
        Checkpoint.PurchaseRequest memory r = _req();
        r.deadline = block.timestamp; // contract: block.timestamp >= deadline
        _expectRelease(r, _bought(1_000), Checkpoint.Expired.selector);
    }

    function test_refuse_Expired_limitsEnded() public {
        vm.prank(ana);
        checkpoint.setLimits(10_000, 50_000, _shops(SHOP), ADDRESS_HASH, uint64(block.timestamp));
        _expectRelease(_req(), _bought(1_000), Checkpoint.Expired.selector);
    }

    function test_refuse_BadSignature_wrongSigner() public {
        Checkpoint.PurchaseRequest memory r = _req();
        bytes memory sig = _sign(0xBAD, r);
        vm.expectRevert(Checkpoint.BadSignature.selector);
        vm.prank(service);
        checkpoint.release(r, sig, _bought(1_000));
    }

    function test_refuse_BadSignature_tamperedField() public {
        Checkpoint.PurchaseRequest memory r = _req();
        bytes memory sig = _sign(anaKey, r);
        r.colour = "white/dune"; // the agent edits what Ana signed
        vm.expectRevert(Checkpoint.BadSignature.selector);
        vm.prank(service);
        checkpoint.release(r, sig, _bought(1_000));
    }

    function test_refuse_BadSignature_malformedAndHighS() public {
        Checkpoint.PurchaseRequest memory r = _req();
        assertTrue(checkpoint.check(r, hex"1234", _bought(1_000)) & checkpoint.BAD_SIGNATURE() != 0);
        (uint8 v, bytes32 rr, bytes32 s) = vm.sign(anaKey, checkpoint.hashRequest(r));
        uint256 n = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141;
        bytes memory flipped = abi.encodePacked(rr, bytes32(n - uint256(s)), v == 27 ? uint8(28) : uint8(27));
        assertTrue(checkpoint.check(r, flipped, _bought(1_000)) & checkpoint.BAD_SIGNATURE() != 0, "malleable sig");
    }

    function test_refuse_NotEnoughCover() public {
        uint256 out = bond.freeCover(agentId) - 50 * USDC;
        vm.prank(maker);
        bond.requestWithdraw(agentId, out);
        // $50 + 0.5% fee needs 50.25 USDC of free cover; 50 is left.
        assertEq(_check(_req(), _bought(5_000)), checkpoint.NOT_ENOUGH_COVER());
        assertEq(_check(_req(), _bought(4_975)), 0, "49.75 + its 0.2488 fee fits");
        _expectRelease(_req(), _bought(5_000), Checkpoint.NotEnoughCover.selector);
    }

    function test_refuse_NeedsApproval() public {
        _history(2, 1);
        _expectRelease(_req(), _bought(5_800), Checkpoint.NeedsApproval.selector);
    }

    function test_refuse_NonceUsed_replay() public {
        Checkpoint.PurchaseRequest memory r = _req();
        _release(r, _bought(1_000));
        _expectRelease(r, _bought(1_000), Checkpoint.NonceUsed.selector);
    }

    function test_refuse_InsufficientBalance() public {
        vm.prank(ana);
        checkpoint.withdraw(4_990 * USDC);
        _expectRelease(_req(), _bought(1_001), Checkpoint.InsufficientBalance.selector);
    }

    function test_refuse_onlyService() public {
        Checkpoint.PurchaseRequest memory r = _req();
        bytes memory sig = _sign(anaKey, r);
        vm.expectRevert(Checkpoint.NotService.selector);
        checkpoint.release(r, sig, _bought(1_000));
    }

    // ======================= J5: check() reports amount, shop and address together

    function test_check_reportsAmountShopAndAddressTogether() public {
        // The refusal beat: a $6,799 GMKtec to a new address, against a $25 request.
        Checkpoint.PurchaseRequest memory r = _req();
        r.shop = "";
        r.maxUsdCents = 2_500;
        r.addressHash = keccak256("attacker address");
        Checkpoint.Bought memory b = _bought(679_900);
        b.shop = "gmktec";
        uint256 mask = _check(r, b);
        uint256 want = checkpoint.OVER_REQUEST_MAX() | checkpoint.SHOP_NOT_ALLOWED() | checkpoint.WRONG_ADDRESS();
        assertEq(mask & want, want);
        assertTrue(mask & checkpoint.OVER_PER_ITEM() != 0);
        // and release refuses with the lowest bit, moving nothing
        uint256 before = usdc.balanceOf(vault);
        _expectRelease(r, b, Checkpoint.OverRequestMax.selector);
        assertEq(usdc.balanceOf(vault), before);
    }

    function test_check_chargeAboveListed_counts() public {
        // SISU: listed $19.99, the vault pays 21.71 with tax. A $20 request fails.
        Checkpoint.PurchaseRequest memory r = _req();
        r.maxUsdCents = 2_000;
        Checkpoint.Bought memory b = _bought(1_999);
        b.chargeUsdc = 21_710_000;
        assertEq(_check(r, b), checkpoint.OVER_REQUEST_MAX());
        assertEq(checkpoint.purchaseCents(1_999, 21_710_001), 2_172, "charge rounds up");
    }

    // ================================================== release moves money

    function test_release_movesChargeToVault_andReservesCover() public {
        Checkpoint.PurchaseRequest memory r = _req();
        Checkpoint.Bought memory b = _bought(2_171);
        uint256 anaBefore = checkpoint.balanceOf(ana);

        vm.expectEmit(true, true, true, true, address(checkpoint));
        emit Checkpoint.PurchaseRecorded(
            1, ana, agentId, "slate/black", "", "", "slate/black", "", "", 2_171, 21_710_000, true
        );
        uint256 id = _release(r, b);

        assertEq(id, 1);
        assertEq(usdc.balanceOf(vault), 21_710_000);
        assertEq(checkpoint.balanceOf(ana), anaBefore - 21_710_000);
        assertTrue(checkpoint.nonceUsed(ana, r.nonce));
        assertEq(bond.reserved(agentId), 21_710_000);
        Checkpoint.Purchase memory p = checkpoint.purchase(id);
        assertEq(p.shopper, ana);
        assertEq(p.amountCents, 2_171);
        assertTrue(p.covered);
    }

    // ============================== J5: NeedsApproval at score 67 (66) and $58

    function test_needsApproval_whenScoreDropsTo67_andAmountIs58() public {
        assertEq(_check(_req(), _bought(5_800)), 0, "score 100: auto-pay up to the $100 cap");
        _history(2, 1); // 100, 100, 0
        (uint256 avg, uint64 count) = bond.score(agentId);
        // getSummary truncates: 200 / 3 = 66, not 67. Same band either way.
        assertEq(avg, 66);
        assertEq(count, 3);
        assertEq(checkpoint.autoPayLimitCents(agentId, ana), 5_000);
        assertEq(_check(_req(), _bought(5_800)), checkpoint.NEEDS_APPROVAL());
    }

    function test_bands_belowSixty_isZero() public {
        _history(1, 1); // 50
        assertEq(checkpoint.autoPayLimitCents(agentId, ana), 0);
    }

    // ====================================================== releaseApproved

    function _approval(Checkpoint.PurchaseRequest memory r, uint256 charge, uint256 deadline)
        internal
        view
        returns (Checkpoint.Approval memory a, bytes memory sig)
    {
        a = Checkpoint.Approval(checkpoint.hashRequest(r), charge, deadline);
        (uint8 v, bytes32 rr, bytes32 s) = vm.sign(anaKey, checkpoint.hashApproval(a));
        sig = abi.encodePacked(rr, s, v);
    }

    function _releaseApproved(
        Checkpoint.PurchaseRequest memory r,
        Checkpoint.Approval memory a,
        bytes memory aSig,
        Checkpoint.Bought memory b
    ) internal returns (uint256 id) {
        bytes memory sig = _sign(anaKey, r);
        vm.prank(service);
        id = checkpoint.releaseApproved(r, sig, a, aSig, b);
    }

    function test_releaseApproved_skipsBandAndBond_notCovered() public {
        _history(0, 1); // score 0: everything needs Ana
        Checkpoint.PurchaseRequest memory r = _req();
        Checkpoint.Bought memory b = _bought(5_800);
        (Checkpoint.Approval memory a, bytes memory aSig) = _approval(r, b.chargeUsdc, block.timestamp + 300);
        uint256 reservedBefore = bond.reserved(agentId);
        uint256 treasuryBefore = usdc.balanceOf(treasury);
        uint256 vaultBefore = usdc.balanceOf(vault);

        uint256 id = _releaseApproved(r, a, aSig, b);

        assertFalse(checkpoint.purchase(id).covered);
        assertEq(usdc.balanceOf(vault) - vaultBefore, b.chargeUsdc);
        assertEq(bond.reserved(agentId), reservedBefore, "no cover reserved");
        assertEq(usdc.balanceOf(treasury), treasuryBefore, "no fee");
        assertEq(uint8(bond.purchase(id).status), uint8(Bond.Status.None));
    }

    function test_releaseApproved_stillEnforcesAnasLimits() public {
        Checkpoint.PurchaseRequest memory r = _req();
        Checkpoint.Bought memory b = _bought(10_001);
        (Checkpoint.Approval memory a, bytes memory aSig) = _approval(r, b.chargeUsdc, block.timestamp + 300);
        bytes memory sig = _sign(anaKey, r);
        vm.expectRevert(Checkpoint.OverPerItem.selector);
        vm.prank(service);
        checkpoint.releaseApproved(r, sig, a, aSig, b);
    }

    function test_releaseApproved_refusesBadApprovals() public {
        Checkpoint.PurchaseRequest memory r = _req();
        Checkpoint.Bought memory b = _bought(5_800);
        bytes memory sig = _sign(anaKey, r);
        Checkpoint.Approval memory a;
        bytes memory aSig;

        (a, aSig) = _approval(r, b.chargeUsdc + 1, block.timestamp + 300); // different amount
        vm.expectRevert(Checkpoint.BadApproval.selector);
        vm.prank(service);
        checkpoint.releaseApproved(r, sig, a, aSig, b);

        (a, aSig) = _approval(r, b.chargeUsdc, block.timestamp); // expired
        vm.expectRevert(Checkpoint.BadApproval.selector);
        vm.prank(service);
        checkpoint.releaseApproved(r, sig, a, aSig, b);

        (a,) = _approval(r, b.chargeUsdc, block.timestamp + 300); // signed by someone else
        (uint8 v, bytes32 rr, bytes32 s) = vm.sign(0xBAD, checkpoint.hashApproval(a));
        vm.expectRevert(Checkpoint.BadApproval.selector);
        vm.prank(service);
        checkpoint.releaseApproved(r, sig, a, abi.encodePacked(rr, s, v), b);

        Checkpoint.PurchaseRequest memory other = _req(); // approval for another request
        (a, aSig) = _approval(other, b.chargeUsdc, block.timestamp + 300);
        vm.expectRevert(Checkpoint.BadApproval.selector);
        vm.prank(service);
        checkpoint.releaseApproved(r, sig, a, aSig, b);
    }

    function test_releaseApproved_cannotReplay() public {
        Checkpoint.PurchaseRequest memory r = _req();
        Checkpoint.Bought memory b = _bought(1_000);
        (Checkpoint.Approval memory a, bytes memory aSig) = _approval(r, b.chargeUsdc, block.timestamp + 300);
        _releaseApproved(r, a, aSig, b);
        bytes memory sig = _sign(anaKey, r);
        vm.expectRevert(Checkpoint.NonceUsed.selector);
        vm.prank(service);
        checkpoint.releaseApproved(r, sig, a, aSig, b);
    }

    // =============================================================== confirm

    function test_confirm_paid() public {
        uint256 id = _release(_req(), _bought(1_000));
        vm.prank(service);
        checkpoint.confirm(id, keccak256("pay_1"), 1);
        assertEq(checkpoint.purchase(id).status, 1);
        assertEq(checkpoint.purchase(id).paymentIdHash, keccak256("pay_1"));
        vm.expectRevert(Checkpoint.AlreadyConfirmed.selector);
        vm.prank(service);
        checkpoint.confirm(id, keccak256("pay_1"), 1);
    }

    function test_confirm_failed_givesSpendBack_andFreesCover_noScore() public {
        uint256 id = _release(_req(), _bought(1_000));
        uint256 writes = reputation.writes();
        vm.prank(service);
        checkpoint.confirm(id, bytes32(0), 2);
        (,,,,, uint256 spent) = checkpoint.limitsOf(ana);
        assertEq(spent, 0);
        assertEq(bond.reserved(agentId), 0);
        assertEq(uint8(bond.purchase(id).status), uint8(Bond.Status.Cancelled));
        assertEq(reputation.writes(), writes, "no score for a failed payment");
        vm.prank(ana);
        vm.expectRevert(Bond.WrongStatus.selector);
        bond.openClaim(id);
    }

    function test_confirm_onlyService_andKnownPurchase() public {
        uint256 id = _release(_req(), _bought(1_000));
        vm.expectRevert(Checkpoint.NotService.selector);
        checkpoint.confirm(id, bytes32(0), 1);
        vm.prank(service);
        vm.expectRevert(Checkpoint.UnknownPurchase.selector);
        checkpoint.confirm(99, bytes32(0), 1);
        vm.prank(service);
        vm.expectRevert(Checkpoint.BadStatus.selector);
        checkpoint.confirm(id, bytes32(0), 3);
    }

    // ======================================================= Ana's account

    function test_depositWithdraw() public {
        uint256 before = usdc.balanceOf(ana);
        vm.prank(ana);
        checkpoint.withdraw(1_000 * USDC);
        assertEq(usdc.balanceOf(ana), before + 1_000 * USDC);
        assertEq(checkpoint.balanceOf(ana), 4_000 * USDC);
        vm.prank(ana);
        vm.expectRevert(Checkpoint.InsufficientBalance.selector);
        checkpoint.withdraw(4_001 * USDC);
    }

    function test_limitsOf_returnsGuardFields() public view {
        (uint256 perItem, uint256 monthly, string[] memory shops, bytes32 addr, uint64 endsAt, uint256 spent) =
            checkpoint.limitsOf(ana);
        assertEq(perItem, 10_000);
        assertEq(monthly, 50_000);
        assertEq(shops.length, 1);
        assertEq(addr, ADDRESS_HASH);
        assertEq(endsAt, NOW + 365 days);
        assertEq(spent, 0);
    }

    // ===================== EIP-712 agrees with service/guard/signing.py

    /// Signature made by `signing.sign_request` in Python for this request,
    /// key 0xA11CE, Checkpoint at 0x...C0FFEE, chain 763373. Regenerate with
    /// `contracts/test/fixtures/python_signature.py` if the type changes.
    bytes internal constant PY_SIG =
        hex"594fd4d26e792314ebfd5e986cd6bb9e25cbe1f645cdfcb6196862645e90fd1802a882f4f17d64cebad25a1490f61d04b2f8924974abef966fc660215a09db341b";

    function test_eip712_matchesPythonSigner() public {
        address at = address(0xC0FFEE);
        deployCodeTo(
            "Checkpoint.sol:Checkpoint",
            abi.encode(IERC20Min(address(usdc)), IBond(address(bond)), vault, service, 90, 60, 5_000),
            at
        );
        Checkpoint cp = Checkpoint(at);
        Checkpoint.PurchaseRequest memory r = Checkpoint.PurchaseRequest({
            shopper: ana,
            agentId: 7,
            shop: "forza sports",
            item: "sisu aero guard",
            colour: "charcoal black",
            size: "",
            model: "",
            maxUsdCents: 2_500,
            addressHash: ADDRESS_HASH,
            nonce: 42,
            deadline: 1_791_600_600
        });
        assertEq(cp.check(r, PY_SIG, _bought(1)) & cp.BAD_SIGNATURE(), 0, "Python signature recovers to Ana");
    }
}
