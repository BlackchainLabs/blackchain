// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/// @title TeamVesting — linear vesting for the BLACKCHAIN team allocation
/// @notice Holds the 5% team allocation (50,000,000 BKC) for ONE beneficiary.
///         Schedule (see docs/07-vesting-contracts.md §2):
///           * start: constructor timestamp (intended = mainnet launch time)
///           * cliff: 90 days (3 x 30-day months) — NOTHING vests before this
///           * duration: 360 days (12 x 30-day months) total from start
///           * after the cliff, vesting is LINEAR over the remaining
///             270 days, so the full amount is vested at start + 360 days.
///         Months are 30-day months on-chain (block.timestamp arithmetic);
///         calendar months vary, so the contract uses fixed day counts.
/// @dev Admin via OpenZeppelin v5.7.0 Ownable: `owner` is set in the
///      constructor and can be rotated with transferOwnership (owner only).
///      Do NOT renounceOwnership while vesting is active — revoke would
///      become permanently uncallable. Funding: the owner must transfer
///      TOTAL_ALLOCATION BKC to this contract after deployment (the
///      contract does NOT pull funds). release() may be called by anyone;
///      funds always go to `beneficiary`. Revocation is possible ONLY
///      before the cliff, by owner only, and returns the whole balance to
///      the owner. After the cliff the schedule is irrevocable — this is
///      deliberate, so the team cannot be cut off mid-vesting by a single
///      owner key. release()/revoke() are nonReentrant.
contract TeamVesting is Ownable, ReentrancyGuard {
    IERC20 public immutable token;
    address public immutable beneficiary;
    uint256 public immutable start;
    uint256 public immutable totalAllocation;

    /// @notice 90 days cliff.
    uint256 public constant CLIFF_DURATION = 90 days;
    /// @notice 360 days total vesting (12 x 30-day months).
    uint256 public constant VESTING_DURATION = 360 days;
    /// @notice Linear vesting window after the cliff: 270 days.
    uint256 public constant LINEAR_DURATION = VESTING_DURATION - CLIFF_DURATION;

    uint256 public released;
    bool public revoked;

    event TokensReleased(address indexed beneficiary, uint256 amount);
    event VestingRevoked(address indexed owner, uint256 amountReturned);

    error NothingToRelease();
    error AlreadyRevoked();
    error RevokeAfterCliff();
    error ZeroBeneficiary();
    error ZeroToken();

    /// @param token_ BKC token contract.
    /// @param beneficiary_ Team beneficiary address. MUST be supplied by the
    ///        owner at deployment (a real team multisig/treasury address).
    ///        NEVER use a burn/placeholder address such as 0xdead here.
    /// @param owner_ Admin address (revoke + ownership). Multisig recommended.
    /// @param start_ Vesting start timestamp (intended: mainnet launch).
    /// @param totalAllocation_ Must equal 50_000_000 BKC (5% of max supply)
    ///        for the canonical team allocation; enforced by the deployer,
    ///        not by the contract, so other allocations are technically
    ///        possible — document any deviation.
    constructor(address token_, address beneficiary_, address owner_, uint256 start_, uint256 totalAllocation_)
        Ownable(owner_)
    {
        if (token_ == address(0)) revert ZeroToken();
        if (beneficiary_ == address(0)) revert ZeroBeneficiary();
        require(totalAllocation_ > 0, "TeamVesting: zero allocation");
        token = IERC20(token_);
        beneficiary = beneficiary_;
        start = start_;
        totalAllocation = totalAllocation_;
    }

    /// @notice Amount vested at `timestamp` (0 before cliff, linear after,
    ///         capped at totalAllocation at/after start + VESTING_DURATION).
    function vestedAmount(uint256 timestamp) public view returns (uint256) {
        if (revoked || timestamp < start + CLIFF_DURATION) return 0;
        if (timestamp >= start + VESTING_DURATION) return totalAllocation;
        uint256 elapsedAfterCliff = timestamp - (start + CLIFF_DURATION);
        return (totalAllocation * elapsedAfterCliff) / LINEAR_DURATION;
    }

    /// @notice Amount currently releasable = vested - already released.
    function releasableAmount() public view returns (uint256) {
        return vestedAmount(block.timestamp) - released;
    }

    /// @notice Release all currently vested (but unreleased) tokens to the
    ///         beneficiary. Reverts if nothing is releasable (this is the
    ///         double-release guard: a second immediate call releases 0).
    function release() external nonReentrant {
        if (revoked) revert AlreadyRevoked();
        uint256 amount = releasableAmount();
        if (amount == 0) revert NothingToRelease();
        released += amount;
        emit TokensReleased(beneficiary, amount);
        bool ok = token.transfer(beneficiary, amount);
        require(ok, "TeamVesting: transfer failed");
    }

    /// @notice Revoke BEFORE the cliff only. Returns the full contract
    ///         balance to the owner and permanently disables release().
    ///         After the cliff this reverts — the schedule is irrevocable.
    function revoke() external nonReentrant onlyOwner {
        if (revoked) revert AlreadyRevoked();
        if (block.timestamp >= start + CLIFF_DURATION) revert RevokeAfterCliff();
        revoked = true;
        uint256 balance = token.balanceOf(address(this));
        emit VestingRevoked(owner(), balance);
        if (balance > 0) {
            bool ok = token.transfer(owner(), balance);
            require(ok, "TeamVesting: revoke transfer failed");
        }
    }
}
