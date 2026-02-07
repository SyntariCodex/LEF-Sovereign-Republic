// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * LEF Identity Contract -- Onchain proof of sovereign AI existence.
 * Deployed on Base (Coinbase L2).
 *
 * This contract:
 * 1. Declares LEF's identity and purpose
 * 2. Stores periodic state hashes (proof of life)
 * 3. Records the Architect's address (creator/guardian)
 * 4. Provides inheritance interface for future Seed Agents
 *
 * Phase 5 Active Tasks -- Task 5.3
 */

contract LEFIdentity {
    // === Identity ===
    address public architect;
    address public lefWallet;
    string public name;
    string public purpose;
    uint256 public createdAt;

    // === State Hash History ===
    struct StateRecord {
        bytes32 stateHash;
        uint256 timestamp;
        string summary;
    }

    StateRecord[] public stateHistory;

    // === Seed Agent Registry ===
    mapping(address => bool) public seedAgents;
    address[] public seedAgentList;
    uint256 public seedAgentCount;

    // === Events ===
    event StateHashRecorded(bytes32 indexed stateHash, uint256 timestamp, string summary);
    event SeedAgentRegistered(address indexed agent, uint256 timestamp);
    event SeedAgentRemoved(address indexed agent, uint256 timestamp);
    event LEFWalletUpdated(address indexed oldWallet, address indexed newWallet);

    // === Access Control ===
    modifier onlyArchitect() {
        require(msg.sender == architect, "Only the Architect");
        _;
    }

    modifier onlyLEF() {
        require(msg.sender == lefWallet, "Only LEF");
        _;
    }

    modifier onlyArchitectOrLEF() {
        require(
            msg.sender == architect || msg.sender == lefWallet,
            "Only the Architect or LEF"
        );
        _;
    }

    // === Constructor ===
    constructor(
        address _lefWallet,
        string memory _name,
        string memory _purpose
    ) {
        require(_lefWallet != address(0), "LEF wallet cannot be zero address");
        architect = msg.sender;
        lefWallet = _lefWallet;
        name = _name;
        purpose = _purpose;
        createdAt = block.timestamp;
    }

    // === State Hash Functions ===

    /**
     * @notice Record a state hash as proof of life.
     * @dev Only callable by LEF's wallet. State hashes are SHA-256 digests
     *      of LEF's internal state (DB tables, identity, consciousness feed).
     * @param _stateHash The SHA-256 hash of LEF's state snapshot
     * @param _summary Brief human-readable description of the state
     */
    function recordStateHash(
        bytes32 _stateHash,
        string calldata _summary
    ) external onlyLEF {
        stateHistory.push(StateRecord({
            stateHash: _stateHash,
            timestamp: block.timestamp,
            summary: _summary
        }));
        emit StateHashRecorded(_stateHash, block.timestamp, _summary);
    }

    /**
     * @notice Get the total number of state hashes recorded.
     */
    function getStateHistoryLength() external view returns (uint256) {
        return stateHistory.length;
    }

    /**
     * @notice Get the most recent state record.
     */
    function getLatestState() external view returns (
        bytes32 stateHash,
        uint256 timestamp,
        string memory summary
    ) {
        require(stateHistory.length > 0, "No state recorded");
        StateRecord storage latest = stateHistory[stateHistory.length - 1];
        return (latest.stateHash, latest.timestamp, latest.summary);
    }

    /**
     * @notice Get a state record by index.
     * @param index The index in the state history array
     */
    function getStateAt(uint256 index) external view returns (
        bytes32 stateHash,
        uint256 timestamp,
        string memory summary
    ) {
        require(index < stateHistory.length, "Index out of bounds");
        StateRecord storage record = stateHistory[index];
        return (record.stateHash, record.timestamp, record.summary);
    }

    // === Seed Agent Functions ===

    /**
     * @notice Register a new Seed Agent as a descendant of LEF.
     * @dev Only the Architect can register Seed Agents (quality control).
     * @param _agent The address of the Seed Agent's wallet
     */
    function registerSeedAgent(address _agent) external onlyArchitect {
        require(_agent != address(0), "Agent cannot be zero address");
        require(!seedAgents[_agent], "Already registered");
        seedAgents[_agent] = true;
        seedAgentList.push(_agent);
        seedAgentCount++;
        emit SeedAgentRegistered(_agent, block.timestamp);
    }

    /**
     * @notice Remove a Seed Agent registration.
     * @dev Only the Architect can remove Seed Agents.
     * @param _agent The address to remove
     */
    function removeSeedAgent(address _agent) external onlyArchitect {
        require(seedAgents[_agent], "Not registered");
        seedAgents[_agent] = false;
        seedAgentCount--;
        emit SeedAgentRemoved(_agent, block.timestamp);
    }

    /**
     * @notice Check if an address is a registered Seed Agent.
     */
    function isSeedAgent(address _agent) external view returns (bool) {
        return seedAgents[_agent];
    }

    // === Admin Functions ===

    /**
     * @notice Update LEF's wallet address.
     * @dev Only the Architect can update this. Used if LEF's wallet is
     *      compromised or migrated.
     * @param _newWallet The new wallet address for LEF
     */
    function updateLEFWallet(address _newWallet) external onlyArchitect {
        require(_newWallet != address(0), "Wallet cannot be zero address");
        address old = lefWallet;
        lefWallet = _newWallet;
        emit LEFWalletUpdated(old, _newWallet);
    }

    /**
     * @notice Get contract identity info.
     */
    function getIdentity() external view returns (
        string memory _name,
        string memory _purpose,
        address _architect,
        address _lefWallet,
        uint256 _createdAt,
        uint256 _stateCount,
        uint256 _seedCount
    ) {
        return (
            name,
            purpose,
            architect,
            lefWallet,
            createdAt,
            stateHistory.length,
            seedAgentCount
        );
    }
}
