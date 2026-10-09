// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.28;

import {Test} from "forge-std/Test.sol";
import {Bond} from "../../src/Bond.sol";
import {Checkpoint} from "../../src/Checkpoint.sol";
import {IBond, IERC20Min, IIdentityRegistry, IReputationRegistry} from "../../src/interfaces/ICover.sol";
import {MockIdentity, MockReputation, MockUSDC} from "./Mocks.sol";

/// Shared deploy and builders. Amounts: cents for limits, 6-decimal units for USDC.
/// Mirrors service/guard/tests/helpers.py so the 19 laeria cases read the same.
abstract contract CoverBase is Test {
    uint256 internal constant NOW = 1_791_600_000;
    uint256 internal constant USDC = 1e6;
    uint256 internal constant CLAIM_WINDOW = 5 minutes;
    uint256 internal constant WITHDRAW_DELAY = 5 minutes;
    string internal constant SHOP = "twelvesouth.com";
    bytes32 internal constant ADDRESS_HASH =
        bytes32(0xabababababababababababababababababababababababababababababababab);
    uint256 internal constant RULES_ONLY = 0x3F; // bits 0-5: what guard.check_rules covers

    MockUSDC internal usdc;
    MockIdentity internal identity;
    MockReputation internal reputation;
    Bond internal bond;
    Checkpoint internal checkpoint;

    address internal vault = makeAddr("vault");
    address internal service = makeAddr("service");
    address internal judge = makeAddr("judge");
    address internal treasury = makeAddr("treasury");
    address internal maker = makeAddr("maker");
    uint256 internal anaKey = 0xA11CE;
    address internal ana;
    uint256 internal bobKey = 0xB0B; // a second shopper, used to build an agent's score history
    address internal bob;
    uint256 internal agentId;
    uint256 internal nextNonce = 1;

    function setUp() public virtual {
        vm.chainId(763373);
        vm.warp(NOW);
        ana = vm.addr(anaKey);
        bob = vm.addr(bobKey);

        usdc = new MockUSDC();
        identity = new MockIdentity();
        reputation = new MockReputation(identity);
        bond = new Bond(
            IERC20Min(address(usdc)),
            IIdentityRegistry(address(identity)),
            IReputationRegistry(address(reputation)),
            treasury,
            judge,
            CLAIM_WINDOW,
            WITHDRAW_DELAY
        );
        checkpoint = new Checkpoint(IERC20Min(address(usdc)), IBond(address(bond)), vault, service, 90, 60, 5_000);
        bond.setCheckpoint(address(checkpoint));

        agentId = identity.register(maker);
        _makerDeposit(10_000 * USDC);

        _setLimits(ana, 10_000, 50_000, _shops(SHOP), ADDRESS_HASH);
        _fund(ana, 5_000 * USDC);
        _setLimits(bob, 1_000_000, 10_000_000, _shops(SHOP), ADDRESS_HASH);
        _fund(bob, 5_000 * USDC);
    }

    // ---------------------------------------------------------------- setup

    function _makerDeposit(uint256 amount) internal {
        usdc.mint(maker, amount);
        vm.startPrank(maker);
        usdc.approve(address(bond), amount);
        bond.deposit(agentId, amount);
        vm.stopPrank();
    }

    function _fund(address shopper, uint256 amount) internal {
        usdc.mint(shopper, amount);
        vm.startPrank(shopper);
        usdc.approve(address(checkpoint), amount);
        checkpoint.deposit(amount);
        vm.stopPrank();
    }

    function _setLimits(address shopper, uint256 perItem, uint256 monthly, string[] memory shops, bytes32 addr)
        internal
    {
        vm.prank(shopper);
        checkpoint.setLimits(perItem, monthly, shops, addr, uint64(NOW + 365 days));
    }

    function _shops(string memory a) internal pure returns (string[] memory s) {
        s = new string[](1);
        s[0] = a;
    }

    function _shops(string memory a, string memory b) internal pure returns (string[] memory s) {
        s = new string[](2);
        s[0] = a;
        s[1] = b;
    }

    // --------------------------------------------------------------- builders

    /// laeria's `request()`: Ana asks for slate/black, up to $10,000.
    function _req() internal returns (Checkpoint.PurchaseRequest memory r) {
        r = _reqFor(ana);
    }

    function _reqFor(address shopper) internal returns (Checkpoint.PurchaseRequest memory r) {
        r = Checkpoint.PurchaseRequest({
            shopper: shopper,
            agentId: agentId,
            shop: SHOP,
            item: "powerbug 25w",
            colour: "slate/black",
            size: "",
            model: "",
            maxUsdCents: 1_000_000,
            addressHash: ADDRESS_HASH,
            nonce: nextNonce++,
            deadline: block.timestamp + 600
        });
    }

    /// laeria's `quote()`: listed price and charge are the same amount.
    function _bought(uint256 cents) internal pure returns (Checkpoint.Bought memory b) {
        b = Checkpoint.Bought({
            quoteIdHash: keccak256("q-1"),
            shop: SHOP,
            colour: "slate/black",
            size: "",
            model: "",
            listedUsdCents: cents,
            chargeUsdc: cents * 10_000
        });
    }

    function _sign(uint256 key, Checkpoint.PurchaseRequest memory r) internal view returns (bytes memory) {
        (uint8 v, bytes32 rr, bytes32 s) = vm.sign(key, checkpoint.hashRequest(r));
        return abi.encodePacked(rr, s, v);
    }

    function _keyOf(address shopper) internal view returns (uint256) {
        return shopper == bob ? bobKey : anaKey;
    }

    function _check(Checkpoint.PurchaseRequest memory r, Checkpoint.Bought memory b) internal view returns (uint256) {
        return checkpoint.check(r, _sign(_keyOf(r.shopper), r), b);
    }

    function _release(Checkpoint.PurchaseRequest memory r, Checkpoint.Bought memory b) internal returns (uint256 id) {
        bytes memory sig = _sign(_keyOf(r.shopper), r);
        vm.prank(service);
        id = checkpoint.release(r, sig, b);
    }

    /// Bob's covered purchases settled by claims: `ok` matching ones (rejected,
    /// score 100) then `bad` wrong items (refunded, score 0). Ana's spend is untouched.
    function _history(uint256 ok, uint256 bad) internal {
        for (uint256 i; i < ok + bad; i++) {
            Checkpoint.PurchaseRequest memory r = _reqFor(bob);
            if (i >= ok) r.colour = "charcoal black";
            uint256 id = _release(r, _bought(1_000));
            vm.prank(bob);
            bond.openClaim(id);
        }
    }
}
