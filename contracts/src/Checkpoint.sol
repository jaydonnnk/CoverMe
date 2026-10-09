// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.28;

import {IBond, IERC20Min} from "./interfaces/ICover.sol";

/// Ana's account: laeria's mandate rules, onchain (3.6).
///
/// Ana sets her limits and deposits USDC. The service can move her money to
/// her Kwal vault only with a request she signed (EIP-712, 3.4) that passes
/// every rule, and the same rules run in `service/guard` before any gas is
/// spent. As in laeria: an unset limit is no allowance, never unlimited.
///
/// `check()` returns every failed rule as a bitmask; bit i is
/// `RULES[i]` in `service/guard/rules.py`. `release` reverts with the error
/// of the lowest failed bit.
contract Checkpoint {
    // ------------------------------------------------------------------ types

    struct PurchaseRequest {
        address shopper;
        uint256 agentId;
        string shop;
        string item;
        string colour;
        string size;
        string model;
        uint256 maxUsdCents;
        bytes32 addressHash;
        uint256 nonce;
        uint256 deadline;
    }

    struct Bought {
        bytes32 quoteIdHash;
        string shop;
        string colour;
        string size;
        string model; // lowercase
        uint256 listedUsdCents; // the item price
        uint256 chargeUsdc; // the quote total, 6 decimals; what moves
    }

    /// A5: Ana approves one uncovered purchase above the agent's auto-pay limit.
    /// `requestDigest` is `hashRequest(r)`, so the approval dies with the nonce.
    struct Approval {
        bytes32 requestDigest;
        uint256 chargeUsdc;
        uint256 deadline;
    }

    struct Limits {
        uint256 perItemMaxCents;
        uint256 monthlyMaxCents;
        bytes32 addressHash;
        uint64 endsAt;
    }

    struct Purchase {
        address shopper;
        uint256 agentId;
        uint256 amountCents; // what the limits counted: max(listed, charge)
        uint256 chargeUsdc;
        uint256 period;
        bytes32 quoteIdHash;
        bytes32 paymentIdHash;
        uint8 status; // 0 released, 1 paid, 2 failed
        bool covered;
    }

    // ------------------------------------------------------- rule bits (append only)

    uint256 public constant OVER_REQUEST_MAX = 1 << 0;
    uint256 public constant OVER_PER_ITEM = 1 << 1;
    uint256 public constant OVER_MONTHLY = 1 << 2;
    uint256 public constant SHOP_NOT_ALLOWED = 1 << 3;
    uint256 public constant WRONG_ADDRESS = 1 << 4;
    uint256 public constant EXPIRED = 1 << 5;
    uint256 public constant BAD_SIGNATURE = 1 << 6;
    uint256 public constant NOT_ENOUGH_COVER = 1 << 7;
    uint256 public constant NEEDS_APPROVAL = 1 << 8;
    uint256 public constant NONCE_USED = 1 << 9;
    uint256 public constant LOW_BALANCE = 1 << 10;

    uint8 public constant PAID = 1;
    uint8 public constant FAILED = 2;

    uint256 public constant PERIOD = 30 days; // the "month" of the monthly cap
    uint256 public constant USDC_UNITS_PER_CENT = 10_000;
    uint256 private constant BPS = 10_000;
    uint256 private constant HALF_N = 0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF5D576E7357A4501DDFE92F46681B20A0;

    bytes32 public constant REQUEST_TYPEHASH = keccak256(
        "PurchaseRequest(address shopper,uint256 agentId,string shop,string item,string colour,string size,string model,uint256 maxUsdCents,bytes32 addressHash,uint256 nonce,uint256 deadline)"
    );
    bytes32 public constant APPROVAL_TYPEHASH =
        keccak256("Approval(bytes32 requestDigest,uint256 chargeUsdc,uint256 deadline)");
    bytes32 private constant DOMAIN_TYPEHASH =
        keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)");

    // ------------------------------------------------------- fixed at deploy

    IERC20Min public immutable usdc;
    IBond public immutable bond;
    address public immutable vault; // Ana's Kwal vault
    address public immutable service;
    uint256 public immutable highBand; // score >= highBand: auto-pay up to Ana's per-item cap
    uint256 public immutable midBand; // score >= midBand: auto-pay up to midCapCents
    uint256 public immutable midCapCents;

    // ----------------------------------------------------------------- state

    mapping(address => Limits) private _limits;
    mapping(address => string[]) private _shops; // lowercase
    mapping(address => mapping(uint256 => uint256)) public spentCents; // shopper => period => cents
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(uint256 => bool)) public nonceUsed;
    mapping(uint256 => Purchase) private _purchases;
    uint256 public purchaseCount;

    // ---------------------------------------------------------------- events

    event LimitsSet(
        address indexed shopper, uint256 perItemMaxCents, uint256 monthlyMaxCents, bytes32 addressHash, uint64 endsAt
    );
    event Deposited(address indexed shopper, uint256 usdc);
    event Withdrawn(address indexed shopper, uint256 usdc);
    event PurchaseRecorded(
        uint256 indexed purchaseId,
        address indexed shopper,
        uint256 indexed agentId,
        string askedColour,
        string askedSize,
        string askedModel,
        string boughtColour,
        string boughtSize,
        string boughtModel,
        uint256 listedUsdCents,
        uint256 chargeUsdc,
        bool covered
    );
    event PurchaseConfirmed(uint256 indexed purchaseId, bytes32 paymentIdHash, uint8 status);

    // ---------------------------------------------------------------- errors

    error OverRequestMax();
    error OverPerItem();
    error OverMonthly();
    error ShopNotAllowed();
    error WrongAddress();
    error Expired();
    error BadSignature();
    error NotEnoughCover();
    error NeedsApproval();
    error NonceUsed();
    error InsufficientBalance();
    error NotService();
    error BadApproval();
    error UnknownPurchase();
    error AlreadyConfirmed();
    error BadStatus();
    error TransferFailed();

    constructor(
        IERC20Min usdc_,
        IBond bond_,
        address vault_,
        address service_,
        uint256 highBand_,
        uint256 midBand_,
        uint256 midCapCents_
    ) {
        usdc = usdc_;
        bond = bond_;
        vault = vault_;
        service = service_;
        highBand = highBand_;
        midBand = midBand_;
        midCapCents = midCapCents_;
    }

    // ------------------------------------------------------------- Ana's side

    /// Replaces Ana's limits. Shops are stored lowercase. Spend so far this
    /// period is kept, so lowering the monthly cap can't reset it.
    function setLimits(
        uint256 perItemMaxCents,
        uint256 monthlyMaxCents,
        string[] calldata shops,
        bytes32 addressHash,
        uint64 endsAt
    ) external {
        _limits[msg.sender] = Limits(perItemMaxCents, monthlyMaxCents, addressHash, endsAt);
        delete _shops[msg.sender];
        for (uint256 i; i < shops.length; i++) {
            _shops[msg.sender].push(string(_lower(shops[i])));
        }
        emit LimitsSet(msg.sender, perItemMaxCents, monthlyMaxCents, addressHash, endsAt);
    }

    function deposit(uint256 amount) external {
        balanceOf[msg.sender] += amount;
        _pull(msg.sender, amount);
        emit Deposited(msg.sender, amount);
    }

    function withdraw(uint256 amount) external {
        if (balanceOf[msg.sender] < amount) revert InsufficientBalance();
        balanceOf[msg.sender] -= amount;
        _push(msg.sender, amount);
        emit Withdrawn(msg.sender, amount);
    }

    /// The 3.2 `Limits` fields, for `chain.get_limits(shopper)`.
    function limitsOf(address shopper)
        external
        view
        returns (
            uint256 perItemMaxCents,
            uint256 monthlyMaxCents,
            string[] memory shops,
            bytes32 addressHash,
            uint64 endsAt,
            uint256 spentThisMonthCents
        )
    {
        Limits storage l = _limits[shopper];
        return (
            l.perItemMaxCents,
            l.monthlyMaxCents,
            _shops[shopper],
            l.addressHash,
            l.endsAt,
            spentCents[shopper][currentPeriod()]
        );
    }

    // ---------------------------------------------------------------- rules

    /// Every failed rule for a covered purchase, as a bitmask. 0 = `release` succeeds.
    function check(PurchaseRequest calldata r, bytes calldata sig, Bought calldata b)
        external
        view
        returns (uint256 failedRules)
    {
        return _failed(r, sig, b, true);
    }

    /// The agent's score band (3.6, J1 item 8): 90+ gets Ana's per-item cap,
    /// 60-89 gets `midCapCents`, under 60 gets 0 (every purchase needs Ana).
    function autoPayLimitCents(uint256 agentId, address shopper) public view returns (uint256) {
        (uint256 avg,) = bond.score(agentId);
        if (avg >= highBand) return _limits[shopper].perItemMaxCents;
        if (avg >= midBand) return midCapCents;
        return 0;
    }

    /// The amount every limit compares: max(listed price, charge rounded up to cents),
    /// the same as `rules.purchase_cents` in the guard.
    function purchaseCents(uint256 listedUsdCents, uint256 chargeUsdc) public pure returns (uint256) {
        uint256 chargeCents = (chargeUsdc + USDC_UNITS_PER_CENT - 1) / USDC_UNITS_PER_CENT;
        return listedUsdCents > chargeCents ? listedUsdCents : chargeCents;
    }

    function currentPeriod() public view returns (uint256) {
        return block.timestamp / PERIOD;
    }

    // ------------------------------------------------------------ service side

    /// Covered purchase: moves `chargeUsdc` from Ana's balance to her Kwal vault
    /// and reserves the same amount of the maker's cover in the Bond.
    function release(PurchaseRequest calldata r, bytes calldata sig, Bought calldata b)
        external
        returns (uint256 purchaseId)
    {
        if (msg.sender != service) revert NotService();
        _revertFirst(_failed(r, sig, b, true));
        purchaseId = _record(r, b, true);
        bond.reserve(purchaseId, r.agentId, r.shopper, b.chargeUsdc, askedHash(r, b), boughtHash(b));
    }

    /// A5 fallback: Ana approved this purchase herself. Her limits still apply;
    /// the score band and the Bond don't, so it is not covered.
    function releaseApproved(
        PurchaseRequest calldata r,
        bytes calldata sig,
        Approval calldata a,
        bytes calldata approvalSig,
        Bought calldata b
    ) external returns (uint256 purchaseId) {
        if (msg.sender != service) revert NotService();
        _revertFirst(_failed(r, sig, b, false));
        if (
            a.requestDigest != hashRequest(r) || a.chargeUsdc != b.chargeUsdc || block.timestamp >= a.deadline
                || _recover(hashApproval(a), approvalSig) != r.shopper
        ) revert BadApproval();
        purchaseId = _record(r, b, false);
    }

    /// The Kwal payment's outcome. A failed payment gives the month's spend
    /// back and frees the maker's cover (the USDC is already in Ana's vault).
    function confirm(uint256 purchaseId, bytes32 paymentIdHash, uint8 status) external {
        if (msg.sender != service) revert NotService();
        Purchase storage p = _purchases[purchaseId];
        if (p.shopper == address(0)) revert UnknownPurchase();
        if (p.status != 0) revert AlreadyConfirmed();
        if (status != PAID && status != FAILED) revert BadStatus();
        p.status = status;
        p.paymentIdHash = paymentIdHash;
        if (status == FAILED) {
            spentCents[p.shopper][p.period] -= p.amountCents;
            if (p.covered) bond.cancelReserve(purchaseId);
        }
        emit PurchaseConfirmed(purchaseId, paymentIdHash, status);
    }

    function purchase(uint256 purchaseId) external view returns (Purchase memory) {
        return _purchases[purchaseId];
    }

    // ----------------------------------------------------------------- EIP-712

    function domainSeparator() public view returns (bytes32) {
        return keccak256(abi.encode(DOMAIN_TYPEHASH, keccak256("Cover"), keccak256("1"), block.chainid, address(this)));
    }

    /// The request's EIP-712 digest: what Ana signs, and the service's `request_id`.
    function hashRequest(PurchaseRequest calldata r) public view returns (bytes32) {
        // Two halves of abi.encode are byte-identical to one call; split for the stack.
        bytes memory head = abi.encode(
            REQUEST_TYPEHASH,
            r.shopper,
            r.agentId,
            keccak256(bytes(r.shop)),
            keccak256(bytes(r.item)),
            keccak256(bytes(r.colour))
        );
        bytes memory tail = abi.encode(
            keccak256(bytes(r.size)), keccak256(bytes(r.model)), r.maxUsdCents, r.addressHash, r.nonce, r.deadline
        );
        return keccak256(abi.encodePacked("\x19\x01", domainSeparator(), keccak256(bytes.concat(head, tail))));
    }

    function hashApproval(Approval calldata a) public view returns (bytes32) {
        bytes32 structHash = keccak256(abi.encode(APPROVAL_TYPEHASH, a.requestDigest, a.chargeUsdc, a.deadline));
        return keccak256(abi.encodePacked("\x19\x01", domainSeparator(), structHash));
    }

    /// What Ana asked for, with each empty ("any") field filled from what was
    /// bought, so a claim compares only the fields she filled in.
    function askedHash(PurchaseRequest calldata r, Bought calldata b) public pure returns (bytes32) {
        return keccak256(
            abi.encode(_lower(_any(r.colour, b.colour)), _lower(_any(r.size, b.size)), _lower(_any(r.model, b.model)))
        );
    }

    function boughtHash(Bought calldata b) public pure returns (bytes32) {
        return keccak256(abi.encode(_lower(b.colour), _lower(b.size), _lower(b.model)));
    }

    // ---------------------------------------------------------------- internal

    function _failed(PurchaseRequest calldata r, bytes calldata sig, Bought calldata b, bool covered)
        internal
        view
        returns (uint256 mask)
    {
        uint256 amount = purchaseCents(b.listedUsdCents, b.chargeUsdc);
        Limits storage l = _limits[r.shopper];

        if (r.maxUsdCents == 0 || amount > r.maxUsdCents) mask |= OVER_REQUEST_MAX;
        if (l.perItemMaxCents == 0 || amount > l.perItemMaxCents) mask |= OVER_PER_ITEM;
        if (l.monthlyMaxCents == 0 || spentCents[r.shopper][currentPeriod()] + amount > l.monthlyMaxCents) {
            mask |= OVER_MONTHLY;
        }
        if (!_shopAllowed(r.shopper, r.shop, b.shop)) mask |= SHOP_NOT_ALLOWED;
        if (l.addressHash == bytes32(0) || r.addressHash != l.addressHash) mask |= WRONG_ADDRESS;
        if (block.timestamp >= r.deadline || block.timestamp >= l.endsAt) mask |= EXPIRED;
        if (r.shopper == address(0) || _recover(hashRequest(r), sig) != r.shopper) mask |= BAD_SIGNATURE;
        if (covered) {
            uint256 fee = b.chargeUsdc * bond.feeBps(r.agentId) / BPS;
            if (b.chargeUsdc + fee > bond.freeCover(r.agentId)) mask |= NOT_ENOUGH_COVER;
            if (amount > autoPayLimitCents(r.agentId, r.shopper)) mask |= NEEDS_APPROVAL;
        }
        if (nonceUsed[r.shopper][r.nonce]) mask |= NONCE_USED;
        if (balanceOf[r.shopper] < b.chargeUsdc) mask |= LOW_BALANCE;
    }

    function _revertFirst(uint256 mask) internal pure {
        if (mask == 0) return;
        if (mask & OVER_REQUEST_MAX != 0) revert OverRequestMax();
        if (mask & OVER_PER_ITEM != 0) revert OverPerItem();
        if (mask & OVER_MONTHLY != 0) revert OverMonthly();
        if (mask & SHOP_NOT_ALLOWED != 0) revert ShopNotAllowed();
        if (mask & WRONG_ADDRESS != 0) revert WrongAddress();
        if (mask & EXPIRED != 0) revert Expired();
        if (mask & BAD_SIGNATURE != 0) revert BadSignature();
        if (mask & NOT_ENOUGH_COVER != 0) revert NotEnoughCover();
        if (mask & NEEDS_APPROVAL != 0) revert NeedsApproval();
        if (mask & NONCE_USED != 0) revert NonceUsed();
        revert InsufficientBalance();
    }

    function _record(PurchaseRequest calldata r, Bought calldata b, bool covered) internal returns (uint256 id) {
        uint256 amount = purchaseCents(b.listedUsdCents, b.chargeUsdc);
        uint256 period = currentPeriod();
        nonceUsed[r.shopper][r.nonce] = true;
        spentCents[r.shopper][period] += amount;
        balanceOf[r.shopper] -= b.chargeUsdc;
        id = ++purchaseCount;
        _purchases[id] = Purchase({
            shopper: r.shopper,
            agentId: r.agentId,
            amountCents: amount,
            chargeUsdc: b.chargeUsdc,
            period: period,
            quoteIdHash: b.quoteIdHash,
            paymentIdHash: bytes32(0),
            status: 0,
            covered: covered
        });
        _push(vault, b.chargeUsdc);
        _emitRecorded(id, r, b, covered);
    }

    function _emitRecorded(uint256 id, PurchaseRequest calldata r, Bought calldata b, bool covered) internal {
        emit PurchaseRecorded(
            id,
            r.shopper,
            r.agentId,
            r.colour,
            r.size,
            r.model,
            b.colour,
            b.size,
            b.model,
            b.listedUsdCents,
            b.chargeUsdc,
            covered
        );
    }

    /// Bought shop must be on Ana's list and, if she signed one, be that shop.
    function _shopAllowed(address shopper, string calldata signedShop, string calldata boughtShop)
        internal
        view
        returns (bool)
    {
        bytes memory bought = _lower(boughtShop);
        if (bought.length == 0) return false;
        bytes32 boughtKey = keccak256(bought);
        if (bytes(signedShop).length != 0 && keccak256(_lower(signedShop)) != boughtKey) return false;
        string[] storage shops = _shops[shopper];
        for (uint256 i; i < shops.length; i++) {
            if (keccak256(bytes(shops[i])) == boughtKey) return true;
        }
        return false;
    }

    /// Plain ECDSA only (Ana's EOA). Anything malformed recovers to address(0).
    function _recover(bytes32 digest, bytes calldata sig) internal pure returns (address) {
        if (sig.length != 65) return address(0);
        bytes32 r;
        bytes32 s;
        uint8 v;
        assembly {
            r := calldataload(sig.offset)
            s := calldataload(add(sig.offset, 32))
            v := byte(0, calldataload(add(sig.offset, 64)))
        }
        if (uint256(s) > HALF_N) return address(0);
        if (v < 27) v += 27;
        if (v != 27 && v != 28) return address(0);
        return ecrecover(digest, v, r, s);
    }

    function _any(string calldata asked, string calldata bought) internal pure returns (string calldata) {
        return bytes(asked).length == 0 ? bought : asked;
    }

    function _lower(string calldata s) internal pure returns (bytes memory out) {
        out = bytes(s);
        for (uint256 i; i < out.length; i++) {
            if (out[i] >= 0x41 && out[i] <= 0x5A) out[i] = bytes1(uint8(out[i]) + 32);
        }
    }

    function _pull(address from, uint256 amount) internal {
        if (!usdc.transferFrom(from, address(this), amount)) revert TransferFailed();
    }

    function _push(address to, uint256 amount) internal {
        if (!usdc.transfer(to, amount)) revert TransferFailed();
    }
}
