// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.28;

import {Test} from "forge-std/Test.sol";

/// Toolchain smoke test only; this does not test any Cover contract logic.
contract ScaffoldTest is Test {
    function test_InkSepoliaChainId() public {
        vm.chainId(763373);
        assertEq(block.chainid, 763373);
    }
}
