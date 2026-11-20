// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @notice Minimal Foundry cheatcode interface, defined locally so the test
///         suite has NO dependency on forge-std or any external library.
///         Only the cheatcodes actually used by these tests are declared.
/// @dev The cheatcode address is Foundry's well-known constant
///      0x7109709ECfa91a80626fF3989D68f67F5b1DD12D (NOT the low 160 bits of
///      keccak256("hevm cheat code address") — that derivation gives a
///      different address and every cheatcode call reverts).
interface Vm {
    function warp(uint256 newTimestamp) external;
    function prank(address msgSender) external;
    function startPrank(address msgSender) external;
    function stopPrank() external;
    function expectRevert(bytes calldata revertData) external;
}

Vm constant vm = Vm(0x7109709ECfa91a80626fF3989D68f67F5b1DD12D);
