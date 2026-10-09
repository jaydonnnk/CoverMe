// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.28;

import {Script, console2} from "forge-std/Script.sol";
import {Bond} from "../src/Bond.sol";
import {Checkpoint} from "../src/Checkpoint.sol";
import {IBond, IERC20Min, IIdentityRegistry, IReputationRegistry} from "../src/interfaces/ICover.sol";

/// J6: deploys Cover's two contracts against Francesco's ERC-8004 registries.
///
///   Bond(usdc, identity, reputation, treasury, judge, claimWindow, withdrawDelay)
///   Checkpoint(usdc, bond, vault, service, 90, 60, 5000)
///   bond.setCheckpoint(checkpoint)        (from the same broadcaster)
///
/// Registries come from DEPLOYMENTS_FILE (default ../deployments/ink-sepolia.json)
/// "registries"; a null Reputation deploys the Bond on its own counters.
/// Everything else comes from env:
///   USDC_ADDRESS, ANA_VAULT_ADDRESS, TREASURY_ADDRESS,
///   SERVICE_ADDRESS or SERVICE_PRIVATE_KEY, JUDGE_ADDRESS or JUDGE_PRIVATE_KEY,
///   CLAIM_WINDOW (seconds, default 180), WITHDRAW_DELAY (seconds, default 300).
///
///   forge script script/Deploy.s.sol --rpc-url $INK_RPC --private-key <deployer> --broadcast
///
/// SPENDS test ETH. Without --broadcast it only simulates. Then run
/// scripts/write_deployments.py to fill "cover".
contract Deploy is Script {
    uint256 public constant HIGH_BAND = 90; // score 90+: auto-pay up to Ana's per-item cap
    uint256 public constant MID_BAND = 60; // 60-89: auto-pay up to $50
    uint256 public constant MID_CAP_CENTS = 5_000;
    uint256 public constant DEFAULT_CLAIM_WINDOW = 180;
    uint256 public constant DEFAULT_WITHDRAW_DELAY = 300;

    struct Config {
        address usdc;
        address identity;
        address reputation; // address(0): counters only
        address vault;
        address service;
        address judge;
        address treasury;
        uint256 claimWindow;
        uint256 withdrawDelay;
    }

    function run() external returns (Bond bond, Checkpoint checkpoint) {
        return deploy(config());
    }

    function config() public view returns (Config memory c) {
        string memory json = vm.readFile(deploymentsFile());
        c.identity = vm.parseJsonAddress(json, ".registries.Identity.address");
        c.reputation = _optionalAddress(json, ".registries.Reputation.address");
        c.usdc = vm.envAddress("USDC_ADDRESS");
        c.vault = vm.envAddress("ANA_VAULT_ADDRESS");
        c.treasury = vm.envAddress("TREASURY_ADDRESS");
        c.service = _role("SERVICE_ADDRESS", "SERVICE_PRIVATE_KEY");
        c.judge = _role("JUDGE_ADDRESS", "JUDGE_PRIVATE_KEY");
        c.claimWindow = vm.envOr("CLAIM_WINDOW", DEFAULT_CLAIM_WINDOW);
        c.withdrawDelay = vm.envOr("WITHDRAW_DELAY", DEFAULT_WITHDRAW_DELAY);
    }

    /// DEPLOYMENTS_FILE is repo-relative (as in .env) unless absolute.
    function deploymentsFile() public view returns (string memory) {
        string memory f = vm.envOr("DEPLOYMENTS_FILE", string("deployments/ink-sepolia.json"));
        if (bytes(f).length != 0 && bytes(f)[0] == "/") return f;
        return string.concat(vm.projectRoot(), "/../", f);
    }

    function deploy(Config memory c) public returns (Bond bond, Checkpoint checkpoint) {
        _check(c);

        vm.startBroadcast();
        bond = new Bond(
            IERC20Min(c.usdc),
            IIdentityRegistry(c.identity),
            IReputationRegistry(c.reputation),
            c.treasury,
            c.judge,
            c.claimWindow,
            c.withdrawDelay
        );
        checkpoint = new Checkpoint(
            IERC20Min(c.usdc), IBond(address(bond)), c.vault, c.service, HIGH_BAND, MID_BAND, MID_CAP_CENTS
        );
        bond.setCheckpoint(address(checkpoint));
        vm.stopBroadcast();

        require(bond.checkpoint() == address(checkpoint), "Bond not pointed at the Checkpoint");
        require(address(checkpoint.bond()) == address(bond), "Checkpoint not pointed at the Bond");

        console2.log("Bond", address(bond));
        console2.log("Checkpoint", address(checkpoint));
        console2.log("Identity", c.identity);
        console2.log("Reputation", c.reputation);
        console2.log("Claim window (s)", c.claimWindow);
        console2.log("Withdraw delay (s)", c.withdrawDelay);
        console2.log("Next: python scripts/write_deployments.py");
    }

    function _check(Config memory c) internal view {
        require(c.usdc.code.length != 0, "USDC_ADDRESS has no code");
        require(c.identity.code.length != 0, "registries.Identity has no code");
        require(c.reputation == address(0) || c.reputation.code.length != 0, "registries.Reputation has no code");
        require(c.vault != address(0), "ANA_VAULT_ADDRESS missing");
        require(c.service != address(0), "service address missing");
        require(c.judge != address(0), "judge address missing");
        require(c.treasury != address(0), "TREASURY_ADDRESS missing");
        require(c.claimWindow != 0, "CLAIM_WINDOW is zero");
    }

    /// An address in the JSON, or address(0) when the key is missing or null.
    function _optionalAddress(string memory json, string memory key) internal view returns (address) {
        if (!vm.keyExistsJson(json, key)) return address(0);
        try vm.parseJsonAddress(json, key) returns (address a) {
            return a;
        } catch {
            return address(0);
        }
    }

    function _role(string memory addressVar, string memory keyVar) internal view returns (address) {
        address a = vm.envOr(addressVar, address(0));
        if (a != address(0)) return a;
        uint256 key = vm.envOr(keyVar, uint256(0));
        return key == 0 ? address(0) : vm.addr(key);
    }
}
