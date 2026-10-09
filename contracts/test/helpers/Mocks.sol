// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.28;

/// 6-decimal test USDC.
contract MockUSDC {
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    uint8 public constant decimals = 6;

    function mint(address to, uint256 amount) external {
        balanceOf[to] += amount;
    }

    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        return true;
    }

    function transfer(address to, uint256 amount) external returns (bool) {
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        allowance[from][msg.sender] -= amount;
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        return true;
    }
}

/// ERC-8004 Identity Registry: just `ownerOf`, like the reference ERC-721.
contract MockIdentity {
    mapping(uint256 => address) internal _owners;
    uint256 public lastId;

    error ERC721NonexistentToken(uint256 tokenId);

    function register(address owner) external returns (uint256 agentId) {
        agentId = ++lastId;
        _owners[agentId] = owner;
    }

    function ownerOf(uint256 agentId) external view returns (address owner) {
        owner = _owners[agentId];
        if (owner == address(0)) revert ERC721NonexistentToken(agentId);
    }

    function isAuthorizedOrOwner(address spender, uint256 agentId) external view returns (bool) {
        return _owners[agentId] == spender;
    }
}

/// ERC-8004 Reputation Registry: the reference `giveFeedback` checks and the
/// reference `getSummary` math (sum / count, truncated, at the mode decimals;
/// Cover only writes 0 decimals, so the mode is 0).
contract MockReputation {
    struct Feedback {
        int128 value;
        uint8 valueDecimals;
        string tag1;
        string tag2;
    }

    MockIdentity public immutable identity;
    mapping(uint256 => mapping(address => Feedback[])) internal _feedback;
    uint256 public writes;
    bool public failWrites;
    bool public failReads;

    constructor(MockIdentity identity_) {
        identity = identity_;
    }

    function setFailWrites(bool v) external {
        failWrites = v;
    }

    function setFailReads(bool v) external {
        failReads = v;
    }

    function giveFeedback(
        uint256 agentId,
        int128 value,
        uint8 valueDecimals,
        string calldata tag1,
        string calldata tag2,
        string calldata,
        string calldata,
        bytes32
    ) external {
        require(!failWrites, "registry down");
        require(valueDecimals <= 18, "too many decimals");
        require(!identity.isAuthorizedOrOwner(msg.sender, agentId), "Self-feedback not allowed");
        _feedback[agentId][msg.sender].push(Feedback(value, valueDecimals, tag1, tag2));
        writes++;
    }

    function feedbackCount(uint256 agentId, address client) external view returns (uint256) {
        return _feedback[agentId][client].length;
    }

    function feedbackAt(uint256 agentId, address client, uint256 i) external view returns (Feedback memory) {
        return _feedback[agentId][client][i];
    }

    function getSummary(uint256 agentId, address[] calldata clients, string calldata tag1, string calldata tag2)
        external
        view
        returns (uint64 count, int128 summaryValue, uint8 summaryValueDecimals)
    {
        require(!failReads, "registry down");
        require(clients.length > 0, "clientAddresses required");
        int256 sum;
        for (uint256 i; i < clients.length; i++) {
            Feedback[] storage list = _feedback[agentId][clients[i]];
            for (uint256 j; j < list.length; j++) {
                if (bytes(tag1).length != 0 && keccak256(bytes(tag1)) != keccak256(bytes(list[j].tag1))) continue;
                if (bytes(tag2).length != 0 && keccak256(bytes(tag2)) != keccak256(bytes(list[j].tag2))) continue;
                sum += int256(list[j].value) * int256(10 ** uint256(18 - list[j].valueDecimals));
                count++;
            }
        }
        if (count == 0) return (0, 0, 0);
        summaryValue = int128((sum / int256(uint256(count))) / 1e18);
        summaryValueDecimals = 0;
    }
}
