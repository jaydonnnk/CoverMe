// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.28;

import {Test} from "forge-std/Test.sol";
import {Sender} from "../src/test-helpers/Sender.sol";
import {SendToVault} from "../script/SendToVault.s.sol";

/// 6-decimal test token. `quiet` mimics a token whose transfer returns nothing;
/// `refuse` one that returns false.
contract MockUSDC {
    mapping(address => uint256) public balanceOf;
    bool public quiet;
    bool public refuse;

    function mint(address to, uint256 amount) external {
        balanceOf[to] += amount;
    }

    function setModes(bool quiet_, bool refuse_) external {
        (quiet, refuse) = (quiet_, refuse_);
    }

    function transfer(address to, uint256 amount) external returns (bool) {
        if (refuse) return false;
        require(balanceOf[msg.sender] >= amount, "balance");
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        if (quiet) {
            assembly { return(0, 0) }
        }
        return true;
    }
}

contract SenderTest is Test {
    address constant VAULT = 0x2dF401bA23216Bc593D052697893554B55Eda0fb;
    uint256 constant HMX_TOTAL = 15_730_000; // 15.73 USDC

    MockUSDC usdc;
    Sender sender;

    function setUp() public {
        usdc = new MockUSDC();
        sender = new Sender(address(usdc));
        usdc.mint(address(sender), 20_000_000);
    }

    function test_SendsTheExactAmount() public {
        vm.expectEmit(address(sender));
        emit Sender.Sent(VAULT, HMX_TOTAL);
        sender.send(VAULT, HMX_TOTAL);
        assertEq(usdc.balanceOf(VAULT), HMX_TOTAL);
        assertEq(usdc.balanceOf(address(sender)), 20_000_000 - HMX_TOTAL);
    }

    function test_OnlyOwnerSendsAndSweeps() public {
        vm.startPrank(address(0xBEEF));
        vm.expectRevert(Sender.NotOwner.selector);
        sender.send(VAULT, 1);
        vm.expectRevert(Sender.NotOwner.selector);
        sender.sweep(address(0xBEEF));
        vm.stopPrank();
    }

    function test_RevertsWhenTheTokenRefuses() public {
        usdc.setModes(false, true);
        vm.expectRevert(Sender.TransferFailed.selector);
        sender.send(VAULT, 1);
    }

    function test_RevertsOnInsufficientBalance() public {
        vm.expectRevert(Sender.TransferFailed.selector);
        sender.send(VAULT, 20_000_001);
    }

    function test_AcceptsATokenThatReturnsNothing() public {
        usdc.setModes(true, false);
        sender.send(VAULT, HMX_TOTAL);
        assertEq(usdc.balanceOf(VAULT), HMX_TOTAL);
    }

    function test_SweepReturnsTheRest() public {
        sender.send(VAULT, HMX_TOTAL);
        sender.sweep(address(this));
        assertEq(usdc.balanceOf(address(sender)), 0);
        assertEq(usdc.balanceOf(address(this)), 20_000_000 - HMX_TOTAL);
    }

    function test_ScriptDeploysTopsUpAndSendsExactly() public {
        SendToVault script = new SendToVault();
        usdc.mint(DEFAULT_SENDER, HMX_TOTAL);
        Sender deployed = script.send(address(usdc), VAULT, address(0), HMX_TOTAL);
        assertEq(deployed.owner(), DEFAULT_SENDER);
        assertEq(usdc.balanceOf(VAULT), HMX_TOTAL);
        assertEq(usdc.balanceOf(address(deployed)), 0);
        assertEq(usdc.balanceOf(DEFAULT_SENDER), 0);
    }

    function test_ScriptReusesAFundedSender() public {
        SendToVault script = new SendToVault();
        vm.prank(DEFAULT_SENDER);
        Sender existing = new Sender(address(usdc));
        usdc.mint(address(existing), HMX_TOTAL);
        script.send(address(usdc), VAULT, address(existing), HMX_TOTAL);
        assertEq(usdc.balanceOf(VAULT), HMX_TOTAL);
        assertEq(usdc.balanceOf(DEFAULT_SENDER), 0); // no top-up needed
    }
}
