// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.28;

import {IERC20Min, IIdentityRegistry, IReputationRegistry} from "./interfaces/ICover.sol";

/// The maker's deposit (3.6): it backs every covered purchase, pays Ana back
/// for a wrong item, charges a cover fee that rises as the agent's score
/// falls, and writes exactly one ERC-8004 score per purchase.
///
/// The Bond is a feedback *client* of the Reputation Registry. It must never
/// be an owner or operator of an agent: the registry refuses self-feedback.
contract Bond {
    enum Status {
        None,
        Reserved, // inside the claim window
        Released, // window passed, no claim: score 100
        Refunded, // wrong item: Ana paid from the deposit, score 0
        Rejected, // claim didn't hold: score 100
        Disputed, // vague claim (A3), waiting for the judge
        NeedsReview, // judge unsure, waiting for the maker
        Cancelled // the Kwal payment failed: no score
    }

    struct Purchase {
        uint256 agentId;
        address shopper;
        uint256 chargeUsdc;
        uint256 feeUsdc;
        bytes32 askedHash;
        bytes32 boughtHash;
        uint64 reservedAt;
        Status status;
    }

    struct Withdrawal {
        uint256 amount;
        uint64 unlockAt;
    }

    uint256 private constant BPS = 10_000;
    uint256 public constant BASE_FEE_BPS = 50;
    uint256 public constant FEE_BPS_PER_POINT = 5;
    uint8 public constant VERDICT_REFUND = 1;
    uint8 public constant VERDICT_REJECT = 2;
    uint8 public constant VERDICT_REVIEW = 3;

    // ------------------------------------------------------- fixed at deploy

    IERC20Min public immutable usdc;
    IIdentityRegistry public immutable identity;
    IReputationRegistry public immutable reputation;
    address public immutable treasury;
    address public immutable judge;
    uint256 public immutable claimWindow; // seconds
    uint256 public immutable withdrawDelay; // seconds
    address private immutable deployer;
    address public checkpoint; // set once, right after the Checkpoint deploys

    // ----------------------------------------------------------------- state

    mapping(uint256 => uint256) public deposited; // includes reserved cover
    mapping(uint256 => uint256) public reserved;
    mapping(uint256 => uint256) public claimsPaid;
    mapping(uint256 => uint256) public feesPaid;
    mapping(uint256 => uint64) public okCount;
    mapping(uint256 => uint64) public wrongCount;
    mapping(uint256 => Withdrawal) public pendingWithdrawal;
    mapping(uint256 => Purchase) private _purchases;

    // ---------------------------------------------------------------- events

    event CheckpointSet(address checkpoint);
    event Deposited(uint256 indexed agentId, address indexed from, uint256 usdc);
    event WithdrawRequested(uint256 indexed agentId, uint256 usdc, uint64 unlockAt);
    event Withdrawn(uint256 indexed agentId, address indexed to, uint256 usdc);
    event Reserved(
        uint256 indexed purchaseId,
        uint256 indexed agentId,
        address indexed shopper,
        uint256 chargeUsdc,
        uint256 feeUsdc
    );
    event ReserveReleased(uint256 indexed purchaseId);
    event ReserveCancelled(uint256 indexed purchaseId);
    event ClaimOpened(uint256 indexed purchaseId, address indexed shopper, bool mismatch);
    event VagueClaimOpened(uint256 indexed purchaseId, address indexed shopper, string complaint);
    event ClaimResolved(uint256 indexed purchaseId, uint8 verdict, bytes32 evidenceHash);
    event Refunded(uint256 indexed purchaseId, address indexed shopper, uint256 usdc);
    event Rejected(uint256 indexed purchaseId);
    event NeedsReview(uint256 indexed purchaseId);
    event ScoreWritten(uint256 indexed purchaseId, uint256 indexed agentId, uint256 value, bool written);

    // ---------------------------------------------------------------- errors

    error NotOwner();
    error NotCheckpoint();
    error NotShopper();
    error NotJudge();
    error NotDeployer();
    error CheckpointAlreadySet();
    error NotEnoughCover();
    error ExceedsFreeCover();
    error NothingToWithdraw();
    error TooEarly();
    error WrongStatus();
    error WindowOpen();
    error WindowClosed();
    error BadVerdict();
    error ZeroAmount();
    error TransferFailed();

    constructor(
        IERC20Min usdc_,
        IIdentityRegistry identity_,
        IReputationRegistry reputation_,
        address treasury_,
        address judge_,
        uint256 claimWindow_,
        uint256 withdrawDelay_
    ) {
        usdc = usdc_;
        identity = identity_;
        reputation = reputation_;
        treasury = treasury_;
        judge = judge_;
        claimWindow = claimWindow_;
        withdrawDelay = withdrawDelay_;
        deployer = msg.sender;
    }

    function setCheckpoint(address checkpoint_) external {
        if (msg.sender != deployer) revert NotDeployer();
        if (checkpoint != address(0)) revert CheckpointAlreadySet();
        checkpoint = checkpoint_;
        emit CheckpointSet(checkpoint_);
    }

    // ------------------------------------------------------------ maker side

    function deposit(uint256 agentId, uint256 amount) external {
        _onlyOwner(agentId);
        if (amount == 0) revert ZeroAmount();
        deposited[agentId] += amount;
        if (!usdc.transferFrom(msg.sender, address(this), amount)) revert TransferFailed();
        emit Deposited(agentId, msg.sender, amount);
    }

    /// Moves free cover into a pending withdrawal. Pending money no longer
    /// backs purchases, so it can never be reserved and withdrawn at once.
    function requestWithdraw(uint256 agentId, uint256 amount) external {
        _onlyOwner(agentId);
        if (amount == 0) revert ZeroAmount();
        if (amount > freeCover(agentId)) revert ExceedsFreeCover();
        Withdrawal storage w = pendingWithdrawal[agentId];
        w.amount += amount;
        w.unlockAt = uint64(block.timestamp + withdrawDelay);
        emit WithdrawRequested(agentId, amount, w.unlockAt);
    }

    function withdraw(uint256 agentId) external {
        _onlyOwner(agentId);
        Withdrawal memory w = pendingWithdrawal[agentId];
        if (w.amount == 0) revert NothingToWithdraw();
        if (block.timestamp < w.unlockAt) revert TooEarly();
        if (deposited[agentId] - reserved[agentId] < w.amount) revert ExceedsFreeCover();
        delete pendingWithdrawal[agentId];
        deposited[agentId] -= w.amount;
        if (!usdc.transfer(msg.sender, w.amount)) revert TransferFailed();
        emit Withdrawn(agentId, msg.sender, w.amount);
    }

    /// The maker's answer to a claim the judge couldn't decide (A3).
    function makerResolve(uint256 purchaseId, bool refund) external {
        Purchase storage p = _purchases[purchaseId];
        _onlyOwner(p.agentId);
        if (p.status != Status.NeedsReview) revert WrongStatus();
        if (refund) _refund(purchaseId, p);
        else _reject(purchaseId, p);
    }

    // ------------------------------------------------------- Checkpoint side

    /// Holds `chargeUsdc` of the maker's cover for this purchase and sends the
    /// cover fee to the treasury. Refuses unless free cover >= charge + fee.
    function reserve(
        uint256 purchaseId,
        uint256 agentId,
        address shopper,
        uint256 chargeUsdc,
        bytes32 askedHash,
        bytes32 boughtHash
    ) external {
        if (msg.sender != checkpoint) revert NotCheckpoint();
        if (_purchases[purchaseId].status != Status.None) revert WrongStatus();
        uint256 fee = chargeUsdc * feeBps(agentId) / BPS;
        if (chargeUsdc + fee > freeCover(agentId)) revert NotEnoughCover();
        deposited[agentId] -= fee;
        reserved[agentId] += chargeUsdc;
        feesPaid[agentId] += fee;
        _purchases[purchaseId] = Purchase({
            agentId: agentId,
            shopper: shopper,
            chargeUsdc: chargeUsdc,
            feeUsdc: fee,
            askedHash: askedHash,
            boughtHash: boughtHash,
            reservedAt: uint64(block.timestamp),
            status: Status.Reserved
        });
        if (fee > 0 && !usdc.transfer(treasury, fee)) revert TransferFailed();
        emit Reserved(purchaseId, agentId, shopper, chargeUsdc, fee);
    }

    /// The Kwal payment failed: free the cover, write no score. The fee stays paid.
    function cancelReserve(uint256 purchaseId) external {
        if (msg.sender != checkpoint) revert NotCheckpoint();
        Purchase storage p = _purchases[purchaseId];
        if (p.status != Status.Reserved) return; // already settled by a claim
        p.status = Status.Cancelled;
        reserved[p.agentId] -= p.chargeUsdc;
        emit ReserveCancelled(purchaseId);
    }

    // -------------------------------------------------------------- outcomes

    /// Anyone, once the claim window has passed without a claim: score 100.
    function releaseReserve(uint256 purchaseId) external {
        Purchase storage p = _purchases[purchaseId];
        if (p.status != Status.Reserved) revert WrongStatus();
        if (block.timestamp < p.reservedAt + claimWindow) revert WindowOpen();
        p.status = Status.Released;
        reserved[p.agentId] -= p.chargeUsdc;
        emit ReserveReleased(purchaseId);
        _writeScore(purchaseId, p, true);
    }

    /// Ana's "Wrong item": the contract compares what she asked for with what
    /// was bought. Mismatch: refund from the deposit, score 0. Match: rejected, score 100.
    function openClaim(uint256 purchaseId) external {
        Purchase storage p = _openable(purchaseId);
        bool mismatch = p.askedHash != p.boughtHash;
        emit ClaimOpened(purchaseId, msg.sender, mismatch);
        if (mismatch) _refund(purchaseId, p);
        else _reject(purchaseId, p);
    }

    /// A3: a complaint the labels can't settle ("it arrived broken"). The
    /// cover stays reserved until the judge (or the maker) decides.
    function openVagueClaim(uint256 purchaseId, string calldata complaint) external {
        Purchase storage p = _openable(purchaseId);
        p.status = Status.Disputed;
        emit VagueClaimOpened(purchaseId, msg.sender, complaint);
    }

    /// Judge only: 1 refund, 2 reject, 3 needs the maker's review.
    function resolveClaim(uint256 purchaseId, uint8 verdict, bytes32 evidenceHash) external {
        if (msg.sender != judge) revert NotJudge();
        Purchase storage p = _purchases[purchaseId];
        if (p.status != Status.Disputed) revert WrongStatus();
        if (verdict == VERDICT_REFUND) {
            _refund(purchaseId, p);
        } else if (verdict == VERDICT_REJECT) {
            _reject(purchaseId, p);
        } else if (verdict == VERDICT_REVIEW) {
            p.status = Status.NeedsReview;
            emit NeedsReview(purchaseId);
        } else {
            revert BadVerdict();
        }
        emit ClaimResolved(purchaseId, verdict, evidenceHash);
    }

    // ----------------------------------------------------------------- views

    /// The agent's average Cover score (0-100) and how many purchases it covers.
    /// No history = 100. Reads the ERC-8004 summary of this Bond's feedback and
    /// falls back to the Bond's own counters if the registry is missing, the
    /// call fails, or it holds fewer writes than the counters (a write failed).
    function score(uint256 agentId) public view returns (uint256 avg, uint64 count) {
        uint64 ok = okCount[agentId];
        uint64 total = ok + wrongCount[agentId];
        if (total == 0) return (100, 0);
        if (address(reputation).code.length != 0) {
            address[] memory clients = new address[](1);
            clients[0] = address(this);
            try reputation.getSummary(agentId, clients, "cover", "") returns (uint64 n, int128 value, uint8 decimals) {
                if (n == total && decimals <= 18) {
                    int256 v = int256(value) / int256(10 ** uint256(decimals));
                    if (v < 0) v = 0;
                    if (v > 100) v = 100;
                    return (uint256(v), n);
                }
            } catch {}
        }
        return (uint256(ok) * 100 / total, total); // truncated, like getSummary
    }

    /// 50 + 5 * (100 - score): 0.5% at 100, 5.5% at 0.
    function feeBps(uint256 agentId) public view returns (uint256) {
        (uint256 avg,) = score(agentId);
        return BASE_FEE_BPS + FEE_BPS_PER_POINT * (100 - avg);
    }

    function freeCover(uint256 agentId) public view returns (uint256) {
        uint256 held = reserved[agentId] + pendingWithdrawal[agentId].amount;
        uint256 total = deposited[agentId];
        return total > held ? total - held : 0;
    }

    function purchase(uint256 purchaseId) external view returns (Purchase memory) {
        return _purchases[purchaseId];
    }

    // -------------------------------------------------------------- internal

    function _onlyOwner(uint256 agentId) internal view {
        if (identity.ownerOf(agentId) != msg.sender) revert NotOwner();
    }

    function _openable(uint256 purchaseId) internal view returns (Purchase storage p) {
        p = _purchases[purchaseId];
        if (msg.sender != p.shopper) revert NotShopper();
        if (p.status != Status.Reserved) revert WrongStatus();
        if (block.timestamp >= p.reservedAt + claimWindow) revert WindowClosed();
    }

    function _refund(uint256 purchaseId, Purchase storage p) internal {
        p.status = Status.Refunded;
        reserved[p.agentId] -= p.chargeUsdc;
        deposited[p.agentId] -= p.chargeUsdc;
        claimsPaid[p.agentId] += p.chargeUsdc;
        if (!usdc.transfer(p.shopper, p.chargeUsdc)) revert TransferFailed();
        emit Refunded(purchaseId, p.shopper, p.chargeUsdc);
        _writeScore(purchaseId, p, false);
    }

    function _reject(uint256 purchaseId, Purchase storage p) internal {
        p.status = Status.Rejected;
        reserved[p.agentId] -= p.chargeUsdc;
        emit Rejected(purchaseId);
        _writeScore(purchaseId, p, true);
    }

    /// The one score write per purchase. Every caller moves the purchase out
    /// of a pending status first, so it can't run twice. A registry failure
    /// never blocks the outcome; the counters still move.
    function _writeScore(uint256 purchaseId, Purchase storage p, bool ok) internal {
        if (ok) okCount[p.agentId]++;
        else wrongCount[p.agentId]++;
        uint256 value = ok ? 100 : 0;
        bool written;
        if (address(reputation).code.length != 0) {
            bytes32 recordHash =
                keccak256(abi.encode(block.chainid, address(this), purchaseId, p.askedHash, p.boughtHash));
            try reputation.giveFeedback(
                p.agentId, int128(int256(value)), 0, "cover", ok ? "ok" : "wrong-item", "", "", recordHash
            ) {
                written = true;
            } catch {}
        }
        emit ScoreWritten(purchaseId, p.agentId, value, written);
    }
}
