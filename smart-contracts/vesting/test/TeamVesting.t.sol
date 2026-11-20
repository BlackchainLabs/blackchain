// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Vm, vm} from "./Vm.sol";
import {BKC} from "../src/BKC.sol";
import {TeamVesting} from "../src/TeamVesting.sol";
import {IERC20Errors} from "@openzeppelin/contracts/interfaces/draft-IERC6093.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @notice Tests for BKC token + TeamVesting. No forge-std: plain `assert`
///         and the local Vm cheatcode interface only. Error selectors for
///         OpenZeppelin failures come from OZ's own error interfaces.
contract BKCTest {
    BKC public token;

    function setUp() public {
        token = new BKC(address(this));
    }

    function testMaxSupplyMintedToDeployer() public view {
        assert(token.totalSupply() == 1_000_000_000 * 10 ** 18);
        assert(token.balanceOf(address(this)) == token.totalSupply());
        assert(token.decimals() == 18);
    }

    function testTransferMovesBalance() public {
        address to = address(0xBEEF);
        token.transfer(to, 100 * 10 ** 18);
        assert(token.balanceOf(to) == 100 * 10 ** 18);
        assert(token.balanceOf(address(this)) == token.totalSupply() - 100 * 10 ** 18);
    }

    function testTransferMoreThanBalanceReverts() public {
        // Precompute BEFORE expectRevert: any call after expectRevert is
        // treated as the "next call" (even totalSupply()), so the amount
        // must already be in a local variable here.
        uint256 tooMuch = 2 * token.totalSupply();
        uint256 available = token.balanceOf(address(this));
        // OpenZeppelin ERC20: ERC20InsufficientBalance(sender, balance, needed).
        vm.expectRevert(
            abi.encodeWithSelector(
                IERC20Errors.ERC20InsufficientBalance.selector, address(this), available, tooMuch
            )
        );
        token.transfer(address(0xBEEF), tooMuch);
    }

    function testTokenNameSymbolDecimals() public view {
        assertEq(token.name(), "Blackchain");
        assertEq(token.symbol(), "BKC");
        assert(token.decimals() == 18);
    }

    function testApproveAndTransferFrom() public {
        address spender = address(0xBEEF);
        address to = address(0xCAFE);
        token.approve(spender, 500 * 10 ** 18);
        assert(token.allowance(address(this), spender) == 500 * 10 ** 18);
        vm.prank(spender);
        token.transferFrom(address(this), to, 200 * 10 ** 18);
        assert(token.balanceOf(to) == 200 * 10 ** 18);
        assert(token.allowance(address(this), spender) == 300 * 10 ** 18);
    }

    function testTransferToZeroAddressReverts() public {
        vm.expectRevert(
            abi.encodeWithSelector(IERC20Errors.ERC20InvalidReceiver.selector, address(0))
        );
        token.transfer(address(0), 1);
    }
}

function assertEq(string memory a, string memory b) pure {
    assert(keccak256(bytes(a)) == keccak256(bytes(b)));
}

contract TeamVestingTest {
    BKC public token;
    TeamVesting public vesting;
    address public beneficiary = address(0x1111111111111111111111111111111111111111);
    address public owner = address(this);
    address public stranger = address(0x2222222222222222222222222222222222222222);
    uint256 public constant TEAM = 50_000_000 * 10 ** 18;
    uint256 public start;

    function setUp() public {
        token = new BKC(address(this));
        start = block.timestamp;
        vesting = new TeamVesting(address(token), beneficiary, owner, start, TEAM);
        token.transfer(address(vesting), TEAM);
    }

    function testZeroVestedBeforeCliff() public view {
        assert(vesting.vestedAmount(block.timestamp) == 0);
        assert(vesting.releasableAmount() == 0);
    }

    function testZeroVestedExactlyAtCliff() public {
        vm.warp(start + 90 days);
        assert(vesting.vestedAmount(block.timestamp) == 0);
    }

    function testReleaseBeforeCliffReverts() public {
        vm.warp(start + 30 days);
        vm.expectRevert(abi.encodeWithSelector(TeamVesting.NothingToRelease.selector));
        vesting.release();
    }

    function testPartialVestedAfterCliff() public {
        // start + 180d: 90d past cliff of a 270d linear window => 1/3 vested.
        vm.warp(start + 180 days);
        assert(vesting.vestedAmount(block.timestamp) == TEAM / 3);
        assert(vesting.releasableAmount() == TEAM / 3);
    }

    function testPartialReleasePaysBeneficiary() public {
        vm.warp(start + 180 days);
        vesting.release();
        assert(token.balanceOf(beneficiary) == TEAM / 3);
        assert(vesting.released() == TEAM / 3);
    }

    function testDoubleReleaseRejected() public {
        vm.warp(start + 180 days);
        vesting.release();
        // Second immediate release: nothing newly vested -> reverts.
        vm.expectRevert(abi.encodeWithSelector(TeamVesting.NothingToRelease.selector));
        vesting.release();
    }

    function testFullVestedAfter12Months() public {
        vm.warp(start + 360 days);
        assert(vesting.vestedAmount(block.timestamp) == TEAM);
    }

    function testFullReleaseAfter12Months() public {
        vm.warp(start + 360 days);
        vesting.release();
        assert(token.balanceOf(beneficiary) == TEAM);
        assert(token.balanceOf(address(vesting)) == 0);
        // Nothing left: further release reverts.
        vm.expectRevert(abi.encodeWithSelector(TeamVesting.NothingToRelease.selector));
        vesting.release();
    }

    function testVestedNeverExceedsTotal() public {
        vm.warp(start + 720 days); // 2 years: still capped at TEAM.
        assert(vesting.vestedAmount(block.timestamp) == TEAM);
    }

    function testRevokeBeforeCliffReturnsFunds() public {
        vm.warp(start + 10 days);
        uint256 before = token.balanceOf(address(this));
        vesting.revoke();
        assert(vesting.revoked());
        assert(token.balanceOf(address(vesting)) == 0);
        assert(token.balanceOf(address(this)) == before + TEAM);
    }

    function testReleaseAfterRevokeReverts() public {
        vesting.revoke();
        vm.warp(start + 360 days);
        vm.expectRevert(abi.encodeWithSelector(TeamVesting.AlreadyRevoked.selector));
        vesting.release();
    }

    function testRevokeAfterCliffReverts() public {
        vm.warp(start + 91 days);
        vm.expectRevert(abi.encodeWithSelector(TeamVesting.RevokeAfterCliff.selector));
        vesting.revoke();
    }

    function testOnlyOwnerCanRevoke() public {
        vm.prank(stranger);
        // OpenZeppelin Ownable: OwnableUnauthorizedAccount(account).
        vm.expectRevert(
            abi.encodeWithSelector(Ownable.OwnableUnauthorizedAccount.selector, stranger)
        );
        vesting.revoke();
    }

    function testOwnerCanTransferOwnership() public {
        // OZ Ownable allows owner rotation; the new owner gains revoke power.
        vesting.transferOwnership(stranger);
        assert(vesting.owner() == stranger);
        vm.prank(owner);
        vm.expectRevert(
            abi.encodeWithSelector(Ownable.OwnableUnauthorizedAccount.selector, owner)
        );
        vesting.revoke();
        vm.prank(stranger);
        vesting.revoke();
        assert(vesting.revoked());
    }

    function testReleaseCallableByAnyonePaysBeneficiary() public {
        vm.warp(start + 360 days);
        vm.prank(stranger);
        vesting.release();
        assert(token.balanceOf(beneficiary) == TEAM);
    }
}
