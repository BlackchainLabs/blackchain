# BLACKCHAIN — Checklist Kesiapan Testnet Publik v0.1 (Sesi 6, 2026-11-20)

**Status:** CHECKLIST — diperbarui tiap sesi. "Siap" berarti sudah ada
bukti (file, node live, atau test lolos), bukan janji. Devnet BKC
terakhir terverifikasi live 20 Nov 2026 22:xx WIB (height 1815,
`catching_up: false`, JSON-RPC 127.0.0.1:8555, `eth_blockNumber` 0x717).

Legenda: ✅ Siap · 🔄 Dikerjakan / sebagian · ⬜ Belum dimulai ·
🔴 Diblokir keputusan pemilik.

## 1. Chain & konsensus

| Item | Status | Bukti / catatan |
|---|---|---|
| Framework (Cosmos SDK + CometBFT + Cosmos EVM) | ✅ Siap | Sesi 1–3; SDK v0.54.5 + Cosmos EVM v0.7.4 |
| EVM live + transfer terbukti | ✅ Siap | Sesi 3 (chain 262144) & Sesi 4 (chain 20261120, tx `0x2ca8d8…`) |
| Identitas BKC (chain ID 20261120, denom abkc) | ✅ Siap | `docs/06-evm-identity-bkc.md`; devnet live |
| Parameter validator (100 validator, slash 5%/1%, inflasi 0%) | ✅ Siap | `docs/06-validator-params.md`; diterapkan di genesis devnet |
| Devnet 1 validator stabil | ✅ Siap | Height 1815 saat checklist ini ditulis |
| Devnet multi-validator (4 node) | ⬜ Belum | Belum pernah dijalankan; butuh sebelum testnet |
| Genesis testnet publik | 🔄 Dikerjakan | Draft devnet ada; genesis testnet final BELUM dibuat (butuh chain ID final + alokasi awal + subsidi testnet dari `docs/06` §5) |
| Jalur ke 100.000 TPS | 🔄 Dikerjakan | Riset & desain selesai (`docs/10`); urutan Fase 1→4 DISETUJUI Sesi 7; desain implementasi Fase 1 selesai (`docs/16`); implementasi BELUM dimulai; plafon realistis tahap 1 ESTIMASI 300–1.000 TPS |
| Audit keamanan chain | ⬜ Belum | Wajib sebelum mainnet; belum dijadwalkan |

## 2. Token & kontrak

| Item | Status | Bukti / catatan |
|---|---|---|
| BKC ERC-20 + TeamVesting + CommunityClaim | ✅ Siap | `forge test` 37/37 (Sesi 5, OpenZeppelin v5.7.0); TANPA deploy |
| Deploy vesting/claim ke Sepolia | 🔄 Dikerjakan | Rencana deploy selesai (`docs/15`): multisig 3-of-5 + timelock 48 jam DIPUTUSKAN. Masih butuh: 5 alamat multisig + beneficiary + timestamp `start` + Merkle root (PLACEHOLDER, wajib diisi pemilik) |
| Pemetaan abkc ↔ BKC ERC-20 | 🔄 Dikerjakan | Desain diputuskan Sesi 7 (`docs/15` §5): opsi (c) tanpa pemetaan untuk Sepolia; opsi (a) mint-burn kanonik sebagai target mainnet + audit |
| Audit kontrak vesting/claim | ⬜ Belum | Belum dijadwalkan |
| Alokasi komunitas 950 jt / tim 50 jt | ✅ Siap (dokumen) | `docs/04-tokenomics.md`; distribusi nyata BELUM terjadi |

## 3. Produk & tooling

| Item | Status | Bukti / catatan |
|---|---|---|
| BlackScan (explorer) | 🔄 Dikerjakan | Spesifikasi v0.1 selesai (`docs/11`); implementasi & deploy BELUM |
| BlackSwap (DEX AMM) | 🔄 Dikerjakan | Spesifikasi v0.1 selesai (`docs/12`); kontrak, test & audit BELUM |
| Faucet testnet | 🔄 Dikerjakan | Spesifikasi v0.1 selesai (`docs/13` A); implementasi BELUM; alokasi dana faucet butuh keputusan |
| Black Wallet | ⬜ Belum | Spesifikasi di whitepaper Bab 14; belum ada spec v0.1 |
| BlackBridge | ⬜ Belum | Desain keamanan di whitepaper Bab 16; TIDAK diluncurkan tanpa audit |
| Panduan validator | ✅ Siap (dokumen) | `docs/13` B + `VALIDATOR_GUIDE.md` |

## 4. Operasional testnet

| Item | Status | Bukti / catatan |
|---|---|---|
| Repo GitHub publik | ✅ Siap | `BlackchainLabs/blackchain`, head `3b165f3e` (Sesi 4+5) |
| Roadmap diperbarui | ✅ Siap | `ROADMAP.md` (status 20 Nov 2026 22:19 WIB) |
| Seed / peer testnet | ⬜ Belum | Belum dipublikasikan; devnet belum buka peer publik |
| Monitoring & alert validator | ⬜ Belum | Panduan ada (`docs/13` B.4); sistem monitoring BELUM dibangun |
| Snapshot sync / state sync | ⬜ Belum | Belum disiapkan |
| Rencana insiden & upgrade | ⬜ Belum | Belum ditulis |
| Komunikasi publik (pengumuman testnet) | 🔴 Diblokir | Butuh persetujuan eksplisit pemilik (aturan misi: pengumuman resmi wajib persetujuan) |

## 5. Blokir — keputusan pemilik yang MASIH TERBUKA (revisi Sesi 7)

Tiga keputusan desain (#1 insentif validator, #2 vesting & kepemilikan,
#3 arah arsitektur TPS) kini **TERPUTUSKAN di level desain** oleh
pemilik (Sesi 7, dokumen `docs/06` §5, `docs/15`, `docs/16`). Yang
tersisa adalah hal-hal konkret yang hanya pemilik yang bisa mengisi
atau menyetujui:

| # | Yang masih dibutuhkan | Dampak bila belum ada | Dokumen |
|---|---|---|---|
| A | **Alamat & parameter vesting** — 5 alamat anggota multisig, alamat beneficiary tim, timestamp `start`, daftar klaim komunitas + Merkle root | Kontrak tidak bisa di-deploy ke Sepolia | `docs/15` §2 |
| B | **Anggaran hardware** — siapa menyediakan & membayar server validator tahap 1 (16 vCPU/64 GB/NVMe) + node RPC/archive | Eksperimen E1/E2 Fase 1 tidak bisa dijalankan; baseline TPS tetap di VM 1,5 CPU | `docs/10` §4, `docs/16` §5.1 |
| C | **Genesis testnet final** — alokasi awal + chain ID final + tanggal buka testnet | Testnet tidak bisa dibuka | `docs/14` §1 |
| D | **Pengumuman resmi testnet** | Butuh persetujuan eksplisit pemilik (aturan misi) | — |

**Aturan yang tetap berlaku:** ketiga keputusan desain di atas diputuskan
oleh pemilik lewat Muse utama, bukan oleh AI. Testnet publik TIDAK
dibuka sebelum blokir A dan C selesai; blokir B tidak menghalangi
testnet (bisa dibuka dengan plafon ~89 TPS yang jujur) tetapi
menghalangi pekerjaan performa Fase 1.

## 6. Ringkasan kesiapan (revisi Sesi 7)

- **Siap:** 11 item · **Dikerjakan/sebagian:** 8 item ·
  **Belum dimulai:** 8 item · **Diblokir hal konkret pemilik:** 4 item
  (A alamat vesting, B anggaran hardware, C genesis final, D pengumuman).
- **Kesimpulan jujur:** testnet BELUM SIAP dibuka hari ini. Yang
  kurang: genesis testnet final, devnet multi-validator, implementasi
  BlackScan/Faucet/BlackSwap, seed/peer, monitoring — plus blokir A
  dan C. Keputusan desain #1/#2/#3 sudah diputuskan (Sesi 7), jadi
  pekerjaan teknis berikutnya tidak lagi menunggu arah — hanya menunggu
  alamat, anggaran, dan eksekusi.
