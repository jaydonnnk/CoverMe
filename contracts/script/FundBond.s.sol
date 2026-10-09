// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.28;

import {Script, console2} from "forge-std/Script.sol";
import {Bond} from "../src/Bond.sol";

interface IERC20Approve {
    function approve(address spender, uint256 amount) external returns (bool);
    function allowance(address owner, address spender) external view returns (uint256);
    function balanceOf(address account) external view returns (uint256);
}

interface IOwnerOf {
    function ownerOf(uint256 tokenId) external view returns (address);
}

/// J6: the maker approves USDC and deposits it into the Bond for its agent.
///
/// Bond address from DEPLOYMENTS_FILE "cover.Bond.address"; agent from
/// AGENT_ID or "registries.agentId". AMOUNT_USDC is in 6-decimal units.
///
///   AMOUNT_USDC=15000000 forge script script/FundBond.s.sol \
///     --rpc-url $INK_RPC --private-key $MAKER_PRIVATE_KEY --broadcast
///
/// SPENDS test USDC (it moves into the Bond as cover) and test ETH.
contract FundBond is Script {
    function run() external {
        string memory json = vm.readFile(_file());
        Bond bond = Bond(vm.parseJsonAddress(json, ".cover.Bond.address"));
        uint256 agentId = vm.envOr("AGENT_ID", uint256(0));
        if (agentId == 0) agentId = vm.parseUint(vm.parseJsonString(json, ".registries.agentId"));
        fund(bond, agentId, vm.envUint("AMOUNT_USDC"));
    }

    function fund(Bond bond, uint256 agentId, uint256 amount) public {
        require(amount > 0, "AMOUNT_USDC is zero");
        IERC20Approve usdc = IERC20Approve(address(bond.usdc()));
        address maker = IOwnerOf(address(bond.identity())).ownerOf(agentId);
        require(usdc.balanceOf(maker) >= amount, "maker holds less USDC than AMOUNT_USDC");
        uint256 before = bond.deposited(agentId);

        vm.startBroadcast();
        if (usdc.allowance(maker, address(bond)) < amount) {
            require(usdc.approve(address(bond), amount), "approve failed");
        }
        bond.deposit(agentId, amount);
        vm.stopBroadcast();

        require(bond.deposited(agentId) == before + amount, "deposit not recorded");
        (uint256 avg, uint64 count) = bond.score(agentId);
        console2.log("Agent", agentId);
        console2.log("Deposited (USDC units)", bond.deposited(agentId));
        console2.log("Free cover (USDC units)", bond.freeCover(agentId));
        console2.log("Score / count", avg, count);
        console2.log("Fee (bps)", bond.feeBps(agentId));
    }

    function _file() internal view returns (string memory) {
        string memory f = vm.envOr("DEPLOYMENTS_FILE", string("deployments/ink-sepolia.json"));
        if (bytes(f).length != 0 && bytes(f)[0] == "/") return f;
        return string.concat(vm.projectRoot(), "/../", f);
    }
}
