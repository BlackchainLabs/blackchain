// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/// @title BKC — Blackchain native coin (ERC-20 representation)
/// @notice ERC-20 built on OpenZeppelin v5.7.0. Max supply is FIXED at
///         deployment: 1_000_000_000 BKC (1e27 units). There is NO mint
///         function after construction and NO burn/pause/admin role on the
///         token itself. The deployer receives the whole supply and is
///         expected to be the treasury / distribution owner that funds
///         TeamVesting and CommunityClaim. On BLACKCHAIN mainnet the native
///         coin lives in Cosmos bank module (base denom "abkc"); this ERC-20
///         is the EVM representation used by the vesting/claim contracts on
///         the EVM side. The bridge/mapping between bank "abkc" and this
///         ERC-20 is OUT OF SCOPE for this spec — it needs a separate,
///         explicit owner decision (see docs/07-vesting-contracts.md).
contract BKC is ERC20 {
    /// @notice Fixed max (and initial) supply: 1_000_000_000 BKC.
    uint256 public constant MAX_SUPPLY = 1_000_000_000 * 10 ** 18;

    /// @param initialHolder Receives the entire fixed supply at deployment.
    ///        In production this MUST be the treasury/distribution address
    ///        chosen by the owner (multisig recommended), never a burn or
    ///        placeholder address.
    constructor(address initialHolder) ERC20("Blackchain", "BKC") {
        require(initialHolder != address(0), "BKC: zero holder");
        _mint(initialHolder, MAX_SUPPLY);
    }
}
