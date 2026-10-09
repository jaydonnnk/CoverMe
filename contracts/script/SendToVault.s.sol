// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.28;

import {Script, console2} from "forge-std/Script.sol";
import {IERC20Transfer, Sender} from "../src/test-helpers/Sender.sol";

/// @notice Handover test 4: send an exact USDC amount from a contract to Ana's
/// Kwal vault. Deploys `Sender` unless SENDER_ADDRESS is set, tops it up from
/// the broadcaster if it holds less than AMOUNT_USDC, then sends exactly
/// AMOUNT_USDC (6-decimal units) to ANA_VAULT_ADDRESS.
///
///   forge script script/SendToVault.s.sol --rpc-url $INK_RPC --private-key <test key> --broadcast
///
/// SPENDS test ETH and test USDC. Without --broadcast it only simulates.
contract SendToVault is Script {
    function run() external returns (Sender sender) {
        return send(
            vm.envAddress("USDC_ADDRESS"),
            vm.envAddress("ANA_VAULT_ADDRESS"),
            vm.envOr("SENDER_ADDRESS", address(0)),
            vm.envUint("AMOUNT_USDC")
        );
    }

    function send(address usdc, address vault, address existing, uint256 amount) public returns (Sender sender) {
        require(amount > 0, "AMOUNT_USDC is zero");
        IERC20Transfer token = IERC20Transfer(usdc);
        uint256 vaultBefore = token.balanceOf(vault);

        vm.startBroadcast();
        sender = existing == address(0) ? new Sender(usdc) : Sender(existing);
        uint256 held = token.balanceOf(address(sender));
        if (held < amount) {
            require(token.transfer(address(sender), amount - held), "top-up failed");
        }
        sender.send(vault, amount);
        vm.stopBroadcast();

        uint256 vaultAfter = token.balanceOf(vault);
        require(vaultAfter - vaultBefore == amount, "vault did not receive the exact amount");
        console2.log("Sender", address(sender));
        console2.log("Sent (USDC units)", amount);
        console2.log("Vault before", vaultBefore);
        console2.log("Vault after", vaultAfter);
        console2.log("Now poll Kwal funding until 'available' rises by the amount; record the time.");
    }
}
