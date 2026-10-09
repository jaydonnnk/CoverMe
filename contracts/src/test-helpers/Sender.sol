// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.28;

interface IERC20Transfer {
    function transfer(address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

/// @notice Handover test 4 helper. Sends an exact USDC amount to Ana's Kwal
/// vault from a contract, the way the Checkpoint's `release` will, to learn
/// whether Kwal counts a contract transfer as funding and how long it takes.
/// Test wallets only; not part of Cover.
contract Sender {
    IERC20Transfer public immutable usdc;
    address public immutable owner;

    event Sent(address indexed to, uint256 amount);

    error NotOwner();
    error TransferFailed();

    constructor(address usdc_) {
        usdc = IERC20Transfer(usdc_);
        owner = msg.sender;
    }

    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner();
        _;
    }

    /// Sends exactly `amount` (6-decimal units) of USDC to `to`.
    function send(address to, uint256 amount) external onlyOwner {
        emit Sent(to, amount);
        _transfer(to, amount);
    }

    /// Returns whatever USDC is left to `to`.
    function sweep(address to) external onlyOwner {
        _transfer(to, usdc.balanceOf(address(this)));
    }

    function _transfer(address to, uint256 amount) private {
        (bool ok, bytes memory data) = address(usdc).call(abi.encodeCall(IERC20Transfer.transfer, (to, amount)));
        if (!ok || (data.length != 0 && !abi.decode(data, (bool)))) revert TransferFailed();
    }
}
