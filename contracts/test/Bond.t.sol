// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.28;

import {Bond} from "../src/Bond.sol";
import {Checkpoint} from "../src/Checkpoint.sol";
import {IERC20Min, IIdentityRegistry, IReputationRegistry} from "../src/interfaces/ICover.sol";
import {MockReputation} from "./helpers/Mocks.sol";
import {CoverBase} from "./helpers/CoverBase.sol";

/// The Bond items of J5's "done when": claims, cover, withdrawals, fee, score.
contract BondTest is CoverBase {
    /// The demo's wrong item: Ana asks for charcoal black, the agent buys snow white ($21.71).
    function _wrongItem() internal returns (uint256 id) {
        Checkpoint.PurchaseRequest memory r = _req();
        r.shop = "";
        r.colour = "charcoal black";
        Checkpoint.Bought memory b = _bought(1_999);
        b.colour = "snow white";
        b.chargeUsdc = 21_710_000;
        id = _release(r, b);
    }

    function _rightItem() internal returns (uint256 id) {
        id = _release(_req(), _bought(4_999));
    }

    // ================================================== claims

    function test_mismatch_refundsAna_fromDeposit_scoreZero() public {
        uint256 id = _wrongItem();
        uint256 anaBefore = usdc.balanceOf(ana);
        uint256 depositBefore = bond.deposited(agentId);

        vm.expectEmit(true, true, false, true, address(bond));
        emit Bond.Refunded(id, ana, 21_710_000);
        vm.prank(ana);
        bond.openClaim(id);

        assertEq(usdc.balanceOf(ana) - anaBefore, 21_710_000, "Ana is paid the charge");
        assertEq(depositBefore - bond.deposited(agentId), 21_710_000, "from the maker's deposit");
        assertEq(bond.claimsPaid(agentId), 21_710_000);
        assertEq(bond.reserved(agentId), 0);
        assertEq(uint8(bond.purchase(id).status), uint8(Bond.Status.Refunded));
        MockReputation.Feedback memory f = reputation.feedbackAt(agentId, address(bond), 0);
        assertEq(f.value, 0);
        assertEq(f.tag1, "cover");
        assertEq(f.tag2, "wrong-item");
        (uint256 avg, uint64 count) = bond.score(agentId);
        assertEq(avg, 0);
        assertEq(count, 1);
    }

    function test_match_isRejected_noMoneyMoves_score100() public {
        uint256 id = _rightItem();
        uint256 anaBefore = usdc.balanceOf(ana);
        uint256 depositBefore = bond.deposited(agentId);
        vm.prank(ana);
        bond.openClaim(id);
        assertEq(usdc.balanceOf(ana), anaBefore);
        assertEq(bond.deposited(agentId), depositBefore);
        assertEq(bond.reserved(agentId), 0);
        assertEq(uint8(bond.purchase(id).status), uint8(Bond.Status.Rejected));
        assertEq(reputation.feedbackAt(agentId, address(bond), 0).value, 100);
        assertEq(reputation.feedbackAt(agentId, address(bond), 0).tag2, "ok");
    }

    function test_emptyAskedField_meansAny_soClaimIsRejected() public {
        Checkpoint.PurchaseRequest memory r = _req();
        r.colour = ""; // Ana didn't pick a colour
        Checkpoint.Bought memory b = _bought(1_000);
        b.colour = "teal";
        uint256 id = _release(r, b);
        vm.prank(ana);
        bond.openClaim(id);
        assertEq(uint8(bond.purchase(id).status), uint8(Bond.Status.Rejected));
    }

    function test_claim_comparesLabelsCaseInsensitively() public {
        Checkpoint.PurchaseRequest memory r = _req();
        r.colour = "Slate/Black";
        uint256 id = _release(r, _bought(1_000));
        vm.prank(ana);
        bond.openClaim(id);
        assertEq(uint8(bond.purchase(id).status), uint8(Bond.Status.Rejected));
    }

    function test_claim_onlyShopper_onlyOnce_onlyInWindow() public {
        uint256 id = _wrongItem();
        uint256 late = _wrongItem(); // bought now: after a refund the score is 0 and buys need Ana
        vm.expectRevert(Bond.NotShopper.selector);
        bond.openClaim(id);

        vm.prank(ana);
        bond.openClaim(id);
        vm.prank(ana);
        vm.expectRevert(Bond.WrongStatus.selector);
        bond.openClaim(id);

        vm.warp(block.timestamp + CLAIM_WINDOW);
        vm.prank(ana);
        vm.expectRevert(Bond.WindowClosed.selector);
        bond.openClaim(late);
    }

    // ================================================== the window

    function test_releaseReserve_afterWindow_anyone_score100() public {
        uint256 id = _rightItem();
        vm.expectRevert(Bond.WindowOpen.selector);
        bond.releaseReserve(id);
        vm.warp(block.timestamp + CLAIM_WINDOW);
        vm.prank(makeAddr("anyone"));
        bond.releaseReserve(id);
        assertEq(bond.reserved(agentId), 0);
        assertEq(uint8(bond.purchase(id).status), uint8(Bond.Status.Released));
        (uint256 avg, uint64 count) = bond.score(agentId);
        assertEq(avg, 100);
        assertEq(count, 1);
    }

    // ================================================== cover

    function test_overReserve_isRefused() public {
        uint256 free = bond.freeCover(agentId);
        vm.prank(address(checkpoint));
        vm.expectRevert(Bond.NotEnoughCover.selector);
        bond.reserve(99, agentId, ana, free, bytes32(0), bytes32(0)); // charge + 0.5% fee > free

        uint256 fits = free * 10_000 / 10_050;
        vm.prank(address(checkpoint));
        bond.reserve(99, agentId, ana, fits, bytes32(0), bytes32(0));
        assertLe(bond.reserved(agentId) + bond.feesPaid(agentId), 10_000 * USDC);
    }

    function test_reserve_onlyCheckpoint_once() public {
        vm.expectRevert(Bond.NotCheckpoint.selector);
        bond.reserve(1, agentId, ana, 1, bytes32(0), bytes32(0));
        uint256 id = _rightItem();
        vm.prank(address(checkpoint));
        vm.expectRevert(Bond.WrongStatus.selector);
        bond.reserve(id, agentId, ana, 1, bytes32(0), bytes32(0));
    }

    function test_cancelReserve_onlyCheckpoint() public {
        uint256 id = _rightItem();
        vm.expectRevert(Bond.NotCheckpoint.selector);
        bond.cancelReserve(id);
    }

    // ================================================== deposits and withdrawals

    function test_deposit_onlyAgentOwner() public {
        usdc.mint(ana, 10 * USDC);
        vm.startPrank(ana);
        usdc.approve(address(bond), 10 * USDC);
        vm.expectRevert(Bond.NotOwner.selector);
        bond.deposit(agentId, 10 * USDC);
        vm.stopPrank();
    }

    function test_withdrawal_isBlockedByReservedCover() public {
        Bond small = _freshBond(100 * USDC);
        uint256 id = 1;
        vm.prank(address(this)); // stands in for the Checkpoint
        small.reserve(id, agentId, ana, 60 * USDC, bytes32(0), bytes32(0)); // + 0.30 fee

        vm.prank(maker);
        vm.expectRevert(Bond.ExceedsFreeCover.selector);
        small.requestWithdraw(agentId, 50 * USDC);

        assertEq(small.freeCover(agentId), 39.7e6);
        vm.prank(maker);
        small.requestWithdraw(agentId, 39.7e6);
        assertEq(small.freeCover(agentId), 0, "pending money no longer backs purchases");

        vm.prank(maker);
        vm.expectRevert(Bond.TooEarly.selector);
        small.withdraw(agentId);

        vm.warp(block.timestamp + WITHDRAW_DELAY);
        vm.prank(maker);
        small.withdraw(agentId);
        assertEq(usdc.balanceOf(maker), 39.7e6);
        assertEq(small.deposited(agentId), 60 * USDC, "the reserved 60 stays");
        assertEq(small.reserved(agentId), 60 * USDC);
    }

    function test_pendingWithdrawal_cannotBeReserved() public {
        Bond small = _freshBond(100 * USDC);
        vm.prank(maker);
        small.requestWithdraw(agentId, 50 * USDC);
        vm.expectRevert(Bond.NotEnoughCover.selector);
        small.reserve(1, agentId, ana, 50 * USDC, bytes32(0), bytes32(0));
    }

    function test_withdraw_onlyOwner() public {
        vm.expectRevert(Bond.NotOwner.selector);
        bond.requestWithdraw(agentId, 1);
    }

    /// A Bond whose Checkpoint is this test contract, with `amount` deposited.
    function _freshBond(uint256 amount) internal returns (Bond b) {
        b = new Bond(
            IERC20Min(address(usdc)),
            IIdentityRegistry(address(identity)),
            IReputationRegistry(address(reputation)),
            treasury,
            judge,
            CLAIM_WINDOW,
            WITHDRAW_DELAY
        );
        b.setCheckpoint(address(this));
        usdc.mint(maker, amount);
        vm.startPrank(maker);
        usdc.approve(address(b), amount);
        b.deposit(agentId, amount);
        vm.stopPrank();
    }

    function test_setCheckpoint_onlyDeployer_once() public {
        vm.expectRevert(Bond.CheckpointAlreadySet.selector);
        bond.setCheckpoint(address(1));
        Bond b = new Bond(
            IERC20Min(address(usdc)),
            IIdentityRegistry(address(identity)),
            IReputationRegistry(address(reputation)),
            treasury,
            judge,
            1,
            1
        );
        vm.prank(maker);
        vm.expectRevert(Bond.NotDeployer.selector);
        b.setCheckpoint(address(1));
    }

    // ================================================== fee

    function test_fee_reachesTreasury_andRisesAsScoreFalls() public {
        assertEq(bond.feeBps(agentId), 50);
        _rightItem(); // $49.99 at 0.5%
        assertEq(usdc.balanceOf(treasury), 249_950);
        assertEq(bond.feesPaid(agentId), 249_950);

        _history(3, 1); // bob: three ok, one wrong; the open purchase above has no score yet
        (uint256 avg,) = bond.score(agentId);
        assertEq(avg, 75);
        assertEq(bond.feeBps(agentId), 175); // 50 + 5 * (100 - 75)

        uint256 before = usdc.balanceOf(treasury);
        _rightItem(); // the same $49.99 now costs the maker 1.75%
        assertEq(usdc.balanceOf(treasury) - before, 874_825);
    }

    function test_fee_atScoreZero_is550() public {
        _history(0, 1);
        assertEq(bond.feeBps(agentId), 550);
    }

    function test_feeAt66_is220() public {
        _history(2, 1);
        assertEq(bond.feeBps(agentId), 220);
    }

    // ================================================== one score per purchase

    function test_oneScorePerPurchase_neverTwo() public {
        uint256 a = _rightItem();
        uint256 b = _wrongItem();
        uint256 c = _rightItem();

        vm.prank(ana);
        bond.openClaim(b); // refund, score 0
        vm.prank(ana);
        bond.openClaim(c); // rejected, score 100
        vm.warp(block.timestamp + CLAIM_WINDOW);
        bond.releaseReserve(a); // released, score 100

        // every second outcome is refused
        vm.expectRevert(Bond.WrongStatus.selector);
        bond.releaseReserve(a);
        vm.expectRevert(Bond.WrongStatus.selector);
        bond.releaseReserve(b);
        vm.expectRevert(Bond.WrongStatus.selector);
        bond.releaseReserve(c);
        vm.prank(ana);
        vm.expectRevert(Bond.WrongStatus.selector);
        bond.openClaim(a);

        assertEq(reputation.feedbackCount(agentId, address(bond)), 3);
        (uint256 avg, uint64 count) = bond.score(agentId);
        assertEq(count, 3);
        assertEq(avg, 66);
    }

    // ================================================== registry failures

    function test_refundStillPays_whenRegistryReverts() public {
        uint256 id = _wrongItem();
        reputation.setFailWrites(true);
        uint256 anaBefore = usdc.balanceOf(ana);

        vm.expectEmit(true, true, false, true, address(bond));
        emit Bond.ScoreWritten(id, agentId, 0, false);
        vm.prank(ana);
        bond.openClaim(id);

        assertEq(usdc.balanceOf(ana) - anaBefore, 21_710_000);
        assertEq(reputation.feedbackCount(agentId, address(bond)), 0);
        (uint256 avg, uint64 count) = bond.score(agentId); // registry has 0 writes, counters 1
        assertEq(avg, 0);
        assertEq(count, 1);
    }

    function test_score_fallsBackToCounters_whenSummaryReverts() public {
        _history(3, 1);
        reputation.setFailReads(true);
        (uint256 avg, uint64 count) = bond.score(agentId);
        assertEq(avg, 75);
        assertEq(count, 4);
    }

    function test_score_noHistory_is100() public view {
        (uint256 avg, uint64 count) = bond.score(agentId);
        assertEq(avg, 100);
        assertEq(count, 0);
    }

    function test_noRegistry_stillWorks() public {
        Bond b = new Bond(
            IERC20Min(address(usdc)),
            IIdentityRegistry(address(identity)),
            IReputationRegistry(address(0)),
            treasury,
            judge,
            CLAIM_WINDOW,
            WITHDRAW_DELAY
        );
        b.setCheckpoint(address(this));
        usdc.mint(maker, 100 * USDC);
        vm.startPrank(maker);
        usdc.approve(address(b), 100 * USDC);
        b.deposit(agentId, 100 * USDC);
        vm.stopPrank();
        b.reserve(1, agentId, ana, 10 * USDC, keccak256("asked"), keccak256("bought"));
        vm.prank(ana);
        b.openClaim(1);
        (uint256 avg, uint64 count) = b.score(agentId);
        assertEq(avg, 0);
        assertEq(count, 1);
    }

    // ================================================== A3 vague claims

    function test_vagueClaim_judgeRefunds() public {
        uint256 id = _rightItem();
        vm.prank(ana);
        bond.openVagueClaim(id, "it arrived cracked");
        vm.warp(block.timestamp + CLAIM_WINDOW);
        vm.expectRevert(Bond.WrongStatus.selector);
        bond.releaseReserve(id); // a disputed reserve doesn't time out

        uint256 anaBefore = usdc.balanceOf(ana);
        vm.prank(judge);
        bond.resolveClaim(id, 1, keccak256("evidence"));
        assertEq(usdc.balanceOf(ana) - anaBefore, 49_990_000);
        assertEq(reputation.feedbackAt(agentId, address(bond), 0).value, 0);
    }

    function test_vagueClaim_judgeRejects() public {
        uint256 id = _rightItem();
        vm.prank(ana);
        bond.openVagueClaim(id, "I changed my mind");
        vm.prank(judge);
        bond.resolveClaim(id, 2, keccak256("evidence"));
        assertEq(uint8(bond.purchase(id).status), uint8(Bond.Status.Rejected));
        assertEq(reputation.feedbackAt(agentId, address(bond), 0).value, 100);
    }

    function test_vagueClaim_review_thenMakerResolves() public {
        uint256 id = _rightItem();
        vm.prank(ana);
        bond.openVagueClaim(id, "not sure it's the right one");
        vm.prank(judge);
        bond.resolveClaim(id, 3, keccak256("evidence"));
        assertEq(uint8(bond.purchase(id).status), uint8(Bond.Status.NeedsReview));
        assertEq(reputation.writes(), 0, "no score until it's settled");

        vm.expectRevert(Bond.NotOwner.selector);
        bond.makerResolve(id, true);
        vm.prank(maker);
        bond.makerResolve(id, true);
        assertEq(uint8(bond.purchase(id).status), uint8(Bond.Status.Refunded));
        assertEq(reputation.writes(), 1);
    }

    function test_resolveClaim_onlyJudge_validVerdict_onlyDisputed() public {
        uint256 id = _rightItem();
        vm.prank(judge);
        vm.expectRevert(Bond.WrongStatus.selector);
        bond.resolveClaim(id, 1, bytes32(0));

        vm.prank(ana);
        bond.openVagueClaim(id, "x");
        vm.expectRevert(Bond.NotJudge.selector);
        bond.resolveClaim(id, 1, bytes32(0));
        vm.prank(judge);
        vm.expectRevert(Bond.BadVerdict.selector);
        bond.resolveClaim(id, 4, bytes32(0));
    }

    function test_vagueClaim_onlyShopper_inWindow() public {
        uint256 id = _rightItem();
        vm.expectRevert(Bond.NotShopper.selector);
        bond.openVagueClaim(id, "x");
        vm.warp(block.timestamp + CLAIM_WINDOW);
        vm.prank(ana);
        vm.expectRevert(Bond.WindowClosed.selector);
        bond.openVagueClaim(id, "x");
    }
}
