# smart-contracts

Bagian dari BLACKCHAIN. Status 20 Nov 2026: PLANNED — belum ada implementasi.
Lihat `docs/02-architecture-design.md` di workspace misi untuk desain v0.1.

## vesting/ (baru, 20 Nov 2026)

Proyek Foundry self-contained untuk token BKC + vesting tim + klaim komunitas.
Lihat spesifikasi lengkap di `../../docs/07-vesting-contracts.md`.

- `src/BKC.sol` — token ERC-20 BKC (max supply tetap 1 miliar BKC)
- `src/TeamVesting.sol` — vesting tim 50 jt BKC, cliff 3 bulan + linear 9 bulan
- `src/CommunityClaim.sol` — klaim airdrop berbasis Merkle proof
- `test/` — unit test Foundry (30 test, semua lolos — lihat dokumen §8)

Status: **SPEC + KODE + TEST — BELUM DIAUDIT, BELUM DI-DEPLOY.**
Jangan deploy sebelum audit dan persetujuan eksplisit Teuku.
