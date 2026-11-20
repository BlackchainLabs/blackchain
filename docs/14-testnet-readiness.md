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
| Genesis testnet publik | 🔄 Dikerjakan | Draft devnet ada; genesis testnet final BELUM dibuat (butuh chain ID final + alokasi awal + keputusan blokir #1/#2) |
| Jalur ke 100.000 TPS | 🔄 Dikerjakan | Riset & desain selesai (`docs/10`); implementasi BELUM dimulai; plafon realistis tahap 1 ESTIMASI 300–1.000 TPS |
| Audit keamanan chain | ⬜ Belum | Wajib sebelum mainnet; belum dijadwalkan |

## 2. Token & kontrak

| Item | Status | Bukti / catatan |
|---|---|---|
| BKC ERC-20 + TeamVesting + CommunityClaim | ✅ Siap | `forge test` 37/37 (Sesi 5, OpenZeppelin v5.7.0); TANPA deploy |
| Deploy vesting/claim ke Sepolia | 🔴 Diblokir | Butuh keputusan pemilik blokir #2 (beneficiary, owner, start, pool klaim, anti-Sybil) + audit |
| Pemetaan abkc ↔ BKC ERC-20 | 🔴 Diblokir | Bagian dari blokir #2; belum ada desain |
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

## 5. Blokir — keputusan pemilik yang MASIH TERBUKA

| # | Keputusan | Dampak bila belum diputuskan | Dokumen |
|---|---|---|---|
| 1 | **Skema insentif validator** — fee-only vs alokasi komunitas / subsidi / inflasi testnet sementara | Validator testnet tidak punya imbal hasil yang jelas; risiko set validator kecil & tidak stabil | `docs/06` (risiko), `docs/14` §4 |
| 2 | **Vesting & klaim** — alamat beneficiary tim, owner (EOA vs multisig vs timelock), timestamp `start`, pool/daftar klaim komunitas + anti-Sybil, pemetaan abkc ↔ BKC ERC-20 | Kontrak tidak bisa di-deploy ke Sepolia; distribusi tidak bisa dimulai | `docs/07` §10 |
| 3 | **Arah arsitektur ke 100.000 TPS** — setujui urutan Fase 1→4 (`docs/10` §7) + anggaran hardware + persetujuan fork Cosmos EVM | Pekerjaan performa tidak bisa dimulai; klaim TPS tetap di ~89 TPS terukur | `docs/10` §9 |

**Aturan:** ketiga blokir di atas TIDAK BOLEH diputuskan oleh AI.
Testnet publik TIDAK dibuka sebelum blokir #1 diputuskan (validator
perlu tahu imbalannya) dan #2 diputuskan (kontrak perlu di-deploy).
Blokir #3 tidak menghalangi testnet — testnet bisa dibuka dengan
plafon ~89 TPS yang jujur — tetapi menghalangi klaim 100.000 TPS.

## 6. Ringkasan kesiapan

- **Siap:** 11 item · **Dikerjakan/sebagian:** 6 item ·
  **Belum dimulai:** 8 item · **Diblokir keputusan pemilik:** 4 item
  (3 keputusan + pengumuman resmi).
- **Kesimpulan jujur:** testnet BELUM SIAP dibuka hari ini. Yang
  kurang: genesis testnet final, devnet multi-validator, implementasi
  BlackScan/Faucet/BlackSwap, seed/peer, monitoring — plus keputusan
  pemilik #1 dan #2. Perkiraan kasar (bukan janji): setelah blokir #1
  dan #2 diputuskan, pekerjaan teknis tersisa berada di orde
  minggu–bulan, bukan hari — dan harus diukur ulang di tiap langkah.
