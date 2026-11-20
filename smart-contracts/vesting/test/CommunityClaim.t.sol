// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Vm, vm} from "./Vm.sol";
import {BKC} from "../src/BKC.sol";
import {CommunityClaim} from "../src/CommunityClaim.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";

/// @notice Tests for CommunityClaim. No forge-std: plain `assert` and the
///         local Vm cheatcode interface only. Error selectors for
///         OpenZeppelin failures come from OZ's own error interfaces.
/// @dev The 4-leaf Merkle tree is built here with the SAME rules the
///      contract documents: leaf = keccak256(abi.encodePacked(account,
///      amount)), sorted-pair hashing at every level.
contract CommunityClaimTest {
    BKC public token;
    CommunityClaim public claimer;
    address public owner = address(this);
    address public stranger = address(0x2222222222222222222222222222222222222222);

    address public alice = address(0xaAaAaAaaAaAaAaaAaAAAAAAAAaaaAaAaAaaAaaAa);
    address public bob = address(0xbBbBBBBbbBBBbbbBbbBbbbbBBbBbbbbBbBbbBBbB);
    address public carol = address(0xCcCCccccCCCCcCCCCCCcCcCccCcCCCcCcccccccC);
    address public dave = address(0xDDdDddDdDdddDDddDDddDDDDdDdDDdDDdDDDDDDd);

    uint256 public constant AMOUNT = 1000 * 10 ** 18;
    bytes32 public root;
    bytes32[] public aliceProof;

    function _leaf(address account, uint256 amount) internal pure returns (bytes32) {
        return keccak256(abi.encodePacked(account, amount));
    }

    function _pair(bytes32 a, bytes32 b) internal pure returns (bytes32) {
        return a <= b ? keccak256(abi.encodePacked(a, b)) : keccak256(abi.encodePacked(b, a));
    }

    function setUp() public {
        token = new BKC(address(this));
        // 4-leaf tree: leaves alice/bob/carol/dave, all AMOUNT.
        bytes32 l0 = _leaf(alice, AMOUNT);
        bytes32 l1 = _leaf(bob, AMOUNT);
        bytes32 l2 = _leaf(carol, AMOUNT);
        bytes32 l3 = _leaf(dave, AMOUNT);
        bytes32 h01 = _pair(l0, l1);
        bytes32 h23 = _pair(l2, l3);
        root = _pair(h01, h23);
        claimer = new CommunityClaim(address(token), owner, root);
        token.transfer(address(claimer), 4 * AMOUNT);
        // Alice's proof: [leaf(bob), h23].
        aliceProof.push(l1);
        aliceProof.push(h23);
    }

    function testClaimSucceedsWithValidProof() public {
        vm.prank(alice);
        claimer.claim(AMOUNT, aliceProof);
        assert(token.balanceOf(alice) == AMOUNT);
        assert(claimer.claimed(alice));
    }

    function testDoubleClaimRejected() public {
        vm.prank(alice);
        claimer.claim(AMOUNT, aliceProof);
        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(CommunityClaim.AlreadyClaimed.selector, alice));
        claimer.claim(AMOUNT, aliceProof);
    }

    function testWrongProofRejected() public {
        // Bob's leaf as proof for Alice: does not match Alice's leaf.
        bytes32[] memory badProof = new bytes32[](2);
        badProof[0] = _leaf(bob, AMOUNT);
        badProof[1] = _leaf(carol, AMOUNT);
        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(CommunityClaim.InvalidProof.selector));
        claimer.claim(AMOUNT, badProof);
    }

    function testWrongAmountRejected() public {
        // Proof is valid for AMOUNT, but claiming a different amount changes
        // the leaf, so verification must fail.
        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(CommunityClaim.InvalidProof.selector));
        claimer.claim(AMOUNT + 1, aliceProof);
    }

    function testNonEligibleAddressRejected() public {
        // Stranger is not in the tree; Alice's proof does not verify for them.
        vm.prank(stranger);
        vm.expectRevert(abi.encodeWithSelector(CommunityClaim.InvalidProof.selector));
        claimer.claim(AMOUNT, aliceProof);
    }

    function testZeroAmountRejected() public {
        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(CommunityClaim.ZeroAmount.selector));
        claimer.claim(0, aliceProof);
    }

    function testOnlyOwnerCanSetRoot() public {
        vm.prank(stranger);
        vm.expectRevert(
            abi.encodeWithSelector(Ownable.OwnableUnauthorizedAccount.selector, stranger)
        );
        claimer.setMerkleRoot(bytes32(uint256(1)));
    }

    function testSetRootByOwnerEnablesNewClaim() public {
        // New single-leaf tree: root == leaf(stranger, AMOUNT), empty proof.
        bytes32 newRoot = _leaf(stranger, AMOUNT);
        claimer.setMerkleRoot(newRoot);
        assert(claimer.merkleRoot() == newRoot);
        bytes32[] memory emptyProof = new bytes32[](0);
        vm.prank(stranger);
        claimer.claim(AMOUNT, emptyProof);
        assert(token.balanceOf(stranger) == AMOUNT);
    }

    function testRootUpdateDoesNotReEnableDoubleClaim() public {
        vm.prank(alice);
        claimer.claim(AMOUNT, aliceProof);
        // Even after a root change, Alice stays claimed.
        claimer.setMerkleRoot(_leaf(alice, AMOUNT));
        bytes32[] memory emptyProof = new bytes32[](0);
        vm.prank(alice);
        vm.expectRevert(abi.encodeWithSelector(CommunityClaim.AlreadyClaimed.selector, alice));
        claimer.claim(AMOUNT, emptyProof);
    }

    function testPauseBlocksClaimAndUnpauseAllows() public {
        claimer.pause();
        assert(claimer.paused());
        vm.prank(alice);
        // OpenZeppelin Pausable: EnforcedPause().
        vm.expectRevert(abi.encodeWithSelector(Pausable.EnforcedPause.selector));
        claimer.claim(AMOUNT, aliceProof);
        claimer.unpause();
        assert(!claimer.paused());
        vm.prank(alice);
        claimer.claim(AMOUNT, aliceProof);
        assert(token.balanceOf(alice) == AMOUNT);
    }

    function testOnlyOwnerCanPause() public {
        vm.prank(stranger);
        vm.expectRevert(
            abi.encodeWithSelector(Ownable.OwnableUnauthorizedAccount.selector, stranger)
        );
        claimer.pause();
    }

    function testOnlyOwnerCanUnpause() public {
        claimer.pause();
        vm.prank(stranger);
        vm.expectRevert(
            abi.encodeWithSelector(Ownable.OwnableUnauthorizedAccount.selector, stranger)
        );
        claimer.unpause();
    }

    function testOnlyOwnerCanRecoverRemaining() public {
        vm.prank(stranger);
        vm.expectRevert(
            abi.encodeWithSelector(Ownable.OwnableUnauthorizedAccount.selector, stranger)
        );
        claimer.recoverRemaining(stranger, AMOUNT);
    }

    function testSetRootWhilePausedAllowed() public {
        // Spec: setMerkleRoot stays callable while paused.
        claimer.pause();
        bytes32 newRoot = _leaf(stranger, AMOUNT);
        claimer.setMerkleRoot(newRoot);
        assert(claimer.merkleRoot() == newRoot);
    }

    function testRecoverRemainingTransfersToOwner() public {
        uint256 before = token.balanceOf(owner);
        claimer.recoverRemaining(owner, AMOUNT);
        assert(token.balanceOf(owner) == before + AMOUNT);
        assert(token.balanceOf(address(claimer)) == 3 * AMOUNT);
    }

    function testRecoverRemainingZeroRecipientReverts() public {
        vm.expectRevert(bytes("CommunityClaim: zero recipient"));
        claimer.recoverRemaining(address(0), AMOUNT);
    }
}
