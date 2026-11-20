// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {MerkleProof} from "@openzeppelin/contracts/utils/cryptography/MerkleProof.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/// @title CommunityClaim — Merkle-proof airdrop claim for the community
/// @notice One claim per address against a Merkle root set by the owner.
///         Leaf construction (MUST match the off-chain tree builder exactly):
///             leaf = keccak256(abi.encodePacked(account, amount))
///         where `amount` is in BKC smallest units (1 BKC = 1e18).
///         Proof verification uses OpenZeppelin v5.7.0
///         MerkleProof.verifyCalldata (sorted-pair hashing): at each level
///         the pair is hashed with the smaller value first. The off-chain
///         tree MUST be built with the same sorted-pair rule.
/// @dev Admin via OpenZeppelin Ownable + Pausable. Funding: the owner must
///      transfer enough BKC to this contract to cover all claims in the
///      current root before claims open. setMerkleRoot() replaces the root
///      — claims already made stay claimed (the `claimed` mapping is never
///      reset), so a root update cannot re-enable a double-claim, but it
///      CAN change who is eligible going forward. Root updates therefore
///      need the same governance care as any fund movement
///      (multisig/timelock recommended). Pausing blocks new claims only;
///      it does not freeze tokens already claimed, and setMerkleRoot stays
///      callable while paused. claim()/recoverRemaining() are nonReentrant.
contract CommunityClaim is Ownable, Pausable, ReentrancyGuard {
    IERC20 public immutable token;

    bytes32 public merkleRoot;
    mapping(address => bool) public claimed;

    event Claimed(address indexed account, uint256 amount);
    event MerkleRootUpdated(bytes32 indexed oldRoot, bytes32 indexed newRoot);
    event RemainingRecovered(address indexed to, uint256 amount);

    error AlreadyClaimed(address account);
    error InvalidProof();
    error ZeroAmount();
    error ZeroToken();

    /// @param token_ BKC token contract.
    /// @param owner_ Admin address (set root, pause, recover). Multisig recommended.
    /// @param merkleRoot_ Initial root; may be bytes32(0) if the tree is not
    ///        ready yet — then no claim can succeed until setMerkleRoot().
    constructor(address token_, address owner_, bytes32 merkleRoot_) Ownable(owner_) {
        if (token_ == address(0)) revert ZeroToken();
        token = IERC20(token_);
        merkleRoot = merkleRoot_;
    }

    /// @notice Set (replace) the Merkle root. Owner only. Emits event.
    function setMerkleRoot(bytes32 newRoot) external onlyOwner {
        bytes32 oldRoot = merkleRoot;
        merkleRoot = newRoot;
        emit MerkleRootUpdated(oldRoot, newRoot);
    }

    /// @notice Pause new claims. Owner only. Emits OZ Paused(owner).
    function pause() external onlyOwner {
        _pause();
    }

    /// @notice Unpause claims. Owner only. Emits OZ Unpaused(owner).
    function unpause() external onlyOwner {
        _unpause();
    }

    /// @notice Claim `amount` BKC for msg.sender with a Merkle proof.
    ///         Exactly once per address, while not paused.
    function claim(uint256 amount, bytes32[] calldata proof) external nonReentrant whenNotPaused {
        if (claimed[msg.sender]) revert AlreadyClaimed(msg.sender);
        if (amount == 0) revert ZeroAmount();
        bytes32 leaf = keccak256(abi.encodePacked(msg.sender, amount));
        if (!MerkleProof.verifyCalldata(proof, merkleRoot, leaf)) revert InvalidProof();
        claimed[msg.sender] = true;
        emit Claimed(msg.sender, amount);
        bool ok = token.transfer(msg.sender, amount);
        require(ok, "CommunityClaim: transfer failed");
    }

    /// @notice Recover unclaimed tokens (e.g. after a campaign ends).
    ///         Owner only. This is a privileged fund movement — in
    ///         production it should be behind a timelock/multisig and
    ///         announced in advance; see docs/07-vesting-contracts.md §7.
    function recoverRemaining(address to, uint256 amount) external nonReentrant onlyOwner {
        require(to != address(0), "CommunityClaim: zero recipient");
        emit RemainingRecovered(to, amount);
        bool ok = token.transfer(to, amount);
        require(ok, "CommunityClaim: transfer failed");
    }
}
