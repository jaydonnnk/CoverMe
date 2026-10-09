// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.28;

import {Bond} from "../src/Bond.sol";
import {Checkpoint} from "../src/Checkpoint.sol";
import {Deploy} from "../script/Deploy.s.sol";
import {FundBond} from "../script/FundBond.s.sol";
import {CoverBase} from "./helpers/CoverBase.sol";
import {MockIdentity, MockReputation, MockUSDC} from "./helpers/Mocks.sol";

/// J6: the deploy script against mocks. setUp deploys through Deploy.deploy()
/// instead of `new`, so the CoverBase builders run on what the script made.
contract DeployTest is CoverBase {
    Deploy internal script;

    function setUp() public override {
        vm.chainId(763373);
        vm.warp(NOW);
        ana = vm.addr(anaKey);
        bob = vm.addr(bobKey);

        usdc = new MockUSDC();
        identity = new MockIdentity();
        reputation = new MockReputation(identity);
        script = new Deploy();
        (bond, checkpoint) = script.deploy(_config(address(reputation)));

        agentId = identity.register(maker);
        _makerDeposit(10_000 * USDC);
        _setLimits(ana, 10_000, 50_000, _shops(SHOP), ADDRESS_HASH);
        _fund(ana, 5_000 * USDC);
    }

    function _config(address rep) internal view returns (Deploy.Config memory c) {
        c = Deploy.Config({
            usdc: address(usdc),
            identity: address(identity),
            reputation: rep,
            vault: vault,
            service: service,
            judge: judge,
            treasury: treasury,
            claimWindow: 180,
            withdrawDelay: 300
        });
    }

    function test_deploy_wiresBondAndCheckpoint() public view {
        assertEq(bond.checkpoint(), address(checkpoint));
        assertEq(address(checkpoint.bond()), address(bond));
        assertEq(address(bond.usdc()), address(usdc));
        assertEq(address(checkpoint.usdc()), address(usdc));
        assertEq(address(bond.identity()), address(identity));
        assertEq(address(bond.reputation()), address(reputation));
        assertEq(bond.treasury(), treasury);
        assertEq(bond.judge(), judge);
        assertEq(bond.claimWindow(), 180);
        assertEq(bond.withdrawDelay(), 300);
        assertEq(checkpoint.vault(), vault);
        assertEq(checkpoint.service(), service);
        assertEq(checkpoint.highBand(), 90);
        assertEq(checkpoint.midBand(), 60);
        assertEq(checkpoint.midCapCents(), 5_000);
    }

    function test_deploy_checkpointCanOnlyBeSetOnce() public {
        vm.expectRevert(Bond.NotDeployer.selector);
        bond.setCheckpoint(address(0xBEEF));
        vm.prank(tx.origin); // the broadcaster that deployed it
        vm.expectRevert(Bond.CheckpointAlreadySet.selector);
        bond.setCheckpoint(address(0xBEEF));
    }

    /// J6 "done when": a fresh agent reads 100 over 0, fee 50 bps.
    function test_deploy_freshAgentScores100OverZero() public view {
        (uint256 avg, uint64 count) = bond.score(agentId + 1);
        assertEq(avg, 100);
        assertEq(count, 0);
        assertEq(bond.feeBps(agentId + 1), 50);
    }

    function test_deploy_coveredPurchaseEndToEnd() public {
        uint256 id = _release(_req(), _bought(2_171));
        assertEq(usdc.balanceOf(vault), 2_171 * 10_000);
        vm.warp(block.timestamp + 180);
        bond.releaseReserve(id);
        (uint256 avg, uint64 count) = bond.score(agentId);
        assertEq(avg, 100);
        assertEq(count, 1);
        assertEq(reputation.writes(), 1);
    }

    function test_deploy_nullReputationRunsOnCounters() public {
        (Bond b, Checkpoint c) = script.deploy(_config(address(0)));
        assertEq(address(b.reputation()), address(0));
        assertEq(b.checkpoint(), address(c));
        (uint256 avg, uint64 count) = b.score(1);
        assertEq(avg, 100);
        assertEq(count, 0);
    }

    function test_deploy_refusesRegistryWithoutCode() public {
        Deploy.Config memory c = _config(address(reputation));
        c.identity = makeAddr("not-a-registry");
        vm.expectRevert(bytes("registries.Identity has no code"));
        script.deploy(c);
    }

    function test_deploy_refusesReputationWithoutCode() public {
        vm.expectRevert(bytes("registries.Reputation has no code"));
        script.deploy(_config(makeAddr("not-a-registry")));
    }

    function test_config_readsRegistriesAndEnv() public {
        vm.setEnv("USDC_ADDRESS", vm.toString(address(usdc)));
        vm.setEnv("ANA_VAULT_ADDRESS", vm.toString(vault));
        vm.setEnv("TREASURY_ADDRESS", vm.toString(treasury));
        vm.setEnv("SERVICE_PRIVATE_KEY", vm.toString(bytes32(uint256(0x5E)))); // address from the key
        vm.setEnv("JUDGE_ADDRESS", vm.toString(judge));
        vm.setEnv("CLAIM_WINDOW", "240");
        vm.setEnv("WITHDRAW_DELAY", "360");

        vm.setEnv("DEPLOYMENTS_FILE", "contracts/test/fixtures/deployments-null-reputation.json");
        Deploy.Config memory c = script.config();
        assertEq(c.identity, 0x5fE095dA5C7Bd3E80E28e59F1e43D250D3e7B620);
        assertEq(c.reputation, address(0));
        assertEq(c.usdc, address(usdc));
        assertEq(c.vault, vault);
        assertEq(c.treasury, treasury);
        assertEq(c.service, vm.addr(0x5E));
        assertEq(c.judge, judge);
        assertEq(c.claimWindow, 240);
        assertEq(c.withdrawDelay, 360);

        vm.setEnv("DEPLOYMENTS_FILE", "contracts/test/fixtures/deployments-with-reputation.json");
        assertEq(script.config().reputation, 0x891513a8C901916D57833201bC2720a63E349a60);
    }

    function test_fundBond_approvesAndDeposits() public {
        // Broadcasts in tests come from tx.origin, so it owns this agent.
        uint256 id = identity.register(tx.origin);
        usdc.mint(tx.origin, 25 * USDC);
        FundBond fund = new FundBond();
        fund.fund(bond, id, 25 * USDC);
        assertEq(bond.deposited(id), 25 * USDC);
        assertEq(bond.freeCover(id), 25 * USDC);
        assertEq(usdc.balanceOf(address(bond)), 10_025 * USDC);
    }

    function test_fundBond_refusesMoreThanTheMakerHolds() public {
        uint256 id = identity.register(tx.origin);
        FundBond fund = new FundBond();
        vm.expectRevert(bytes("maker holds less USDC than AMOUNT_USDC"));
        fund.fund(bond, id, 1);
    }
}
