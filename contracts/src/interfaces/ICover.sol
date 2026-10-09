// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.28;

/// The slice of test USDC Cover uses (6 decimals).
interface IERC20Min {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

/// ERC-8004 Identity Registry (reference contract, deployed unchanged by Francesco).
interface IIdentityRegistry {
    function ownerOf(uint256 agentId) external view returns (address);
}

/// ERC-8004 Reputation Registry (reference contract). `getSummary` averages the
/// non-revoked feedback of the given clients: sum / count, truncated toward
/// zero, at the most common `valueDecimals` (checked in
/// `ReputationRegistryUpgradeable.sol`). Cover always writes 0 decimals.
interface IReputationRegistry {
    function giveFeedback(
        uint256 agentId,
        int128 value,
        uint8 valueDecimals,
        string calldata tag1,
        string calldata tag2,
        string calldata endpoint,
        string calldata feedbackURI,
        bytes32 feedbackHash
    ) external;

    function getSummary(uint256 agentId, address[] calldata clientAddresses, string calldata tag1, string calldata tag2)
        external
        view
        returns (uint64 count, int128 summaryValue, uint8 summaryValueDecimals);
}

/// What the Checkpoint needs from the Bond.
interface IBond {
    function reserve(
        uint256 purchaseId,
        uint256 agentId,
        address shopper,
        uint256 chargeUsdc,
        bytes32 askedHash,
        bytes32 boughtHash
    ) external;
    function cancelReserve(uint256 purchaseId) external;
    function score(uint256 agentId) external view returns (uint256 avg, uint64 count);
    function feeBps(uint256 agentId) external view returns (uint256);
    function freeCover(uint256 agentId) external view returns (uint256);
}
