# BLACKCHAIN — Checklist Kesiapan Testnet Publik v0.1 (Sesi 6, 2026-11-20)

**Status:** CHECKLIST — diperbarui tiap sesi. "Siap" berarti sudah ada
bukti (file, node live, atau test lolos), bukan janji. Testnet rehearsal
4 validator terakhir terverifikasi live 20 Nov 2026 16:52 UTC
(height 472, hash `C73E9F4189E6959D…` sama di keempat node,
`catching_up: false`, JSON-RPC 127.0.0.1:8655/8665/8675/8685,
`eth_blockNumber` cocok) — lihat `docs/17` §8. Devnet BKC 1-validator
lama tetap jalan terpisah (8555). **Sesi 10: paket testnet publik
TERBUKA** (`repo/testnet/` + draft pengumuman `docs/20`) — tetapi
jaringan live masih lokal; belum ada endpoint publik.

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
| Devnet multi-validator (4 node) | ✅ Siap | Rehearsal 4 validator live Sesi 8 (`docs/17`): height sama + hash sama di 4 node, transfer EVM terkonfirmasi di 4 node, liveness 3/4 terbukti. Pelajaran F32/F33 tercatat. |
| Genesis testnet publik | ✅ Siap (draft) | `genesis/blackchain-testnet-genesis.json` — 4 gentx @ 1.000 BKC, total supply genesis 30.080.000 BKC, `genesis validate` LOLOS. Masih DRAFT: keputusan final (pakai apa adanya vs buat ulang) + pemindahan pool subsidi/faucet + tanggal buka ada di `docs/18` §7–§8 |
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
| Seed / peer testnet | 🔄 Dikerjakan | **Paket publik TERBUKA Sesi 10** (`repo/testnet/`: genesis + README + `seeds.md`); daftar seed berisi node ID + alamat 127.0.0.1 rehearsal — seed PUBLIK belum ada (butuh server + IP publik, prasyarat P1). **Sesi 11 (21 Nov 2026): paket deploy VPS SIAP — persiapan, BUKAN selesai** (`repo/testnet/vps-deploy.sh` + `vps-runbook.md` + `docs/21`); VPS sudah disediakan pemilik, tetapi IP/username/OS/konfirmasi kunci SSH belum diterima dan deploy belum dieksekusi — P1 menjadi SEBAGIAN (lihat `docs/21` §6) |
| Monitoring & alert validator | ⬜ Belum | Panduan ada (`docs/13` B.4); sistem monitoring BELUM dibangun |
| Snapshot sync / state sync | ⬜ Belum | Belum disiapkan |
| Rencana insiden & upgrade | ⬜ Belum | Belum ditulis (wajib sebelum pembukaan publik, `docs/18` §6) |
| Paket peluncuran testnet (runbook) | ✅ Siap | `docs/18`: runbook seed/validator/faucet/BlackScan + port/firewall + daftar prasyarat publik P1–P7 |
| Komunikasi publik (pengumuman testnet) | 🔄 Dikerjakan | **Draft selesai Sesi 10** (`docs/20`, ID + EN) — DRAFT, BELUM diposting; butuh persetujuan eksplisit pemilik + tanggal buka + alamat seed publik |
| Paket publik testnet | ✅ Siap | Sesi 10: `repo/testnet/` (genesis + README cara bergabung + `seeds.md` jujur) — publik di GitHub |

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
| B2 | **Akses VPS seed** (bagian dari B) — VPS sudah disediakan pemilik 21 Nov 2026, tetapi IP publik + username SSH + OS/distro + konfirmasi kunci publik di `authorized_keys` belum diterima; deploy seed belum dieksekusi | Tidak ada endpoint publik sampai deploy + verifikasi selesai (runbook §3–§5) | `docs/21`, `repo/testnet/vps-runbook.md` §1 |
| C | **Genesis testnet final + tanggal buka** — draft genesis SUDAH ADA dan teruji (`docs/17` §2, `genesis/blackchain-testnet-genesis.json`); yang tersisa: keputusan pakai-apa-adanya vs buat-ulang, pemindahan pool subsidi (20 jt tBKC) + faucet (10 jt tBKC) dari alamat operator ke community pool/multisig, dan tanggal buka testnet | Testnet tidak bisa dibuka | `docs/18` §7–§8 |
| D | **Pengumuman resmi testnet** | Butuh persetujuan eksplisit pemilik (aturan misi) | — |

**Aturan yang tetap berlaku:** ketiga keputusan desain di atas diputuskan
oleh pemilik lewat Muse utama, bukan oleh AI. Testnet publik TIDAK
dibuka sebelum blokir A dan C selesai; blokir B tidak menghalangi
testnet (bisa dibuka dengan plafon ~89 TPS yang jujur) tetapi
menghalangi pekerjaan performa Fase 1.

## 6. Ringkasan kesiapan (revisi Sesi 10)

- **Siap:** 14 item · **Dikerjakan/sebagian:** 7 item ·
  **Belum dimulai:** 7 item · **Diblokir komunikasi:** 0 item (draft
  pengumuman sudah ada, menunggu persetujuan) · **Blokir konkret
  pemilik:** 4 item (A alamat vesting, B anggaran hardware/server+domain,
  C keputusan genesis final + tanggal buka, D persetujuan pengumuman).
  **Sesi 11 (21 Nov 2026):** paket deploy seed VPS SIAP (persiapan) —
  hitungan TIDAK berubah karena belum ada item yang pindah ke Siap;
  P1 menjadi SEBAGIAN (VPS sudah disediakan pemilik; akses belum
  diterima; deploy belum dieksekusi) — lihat `docs/21` §6.
- **Kesimpulan jujur:** **paket testnet publik TERBUKA** (genesis +
  panduan + seed list jujur + draft pengumuman), dan chain-nya SUDAH
  TERBUKTI BERJALAN (rehearsal 4 validator: sinkron height 472, transfer
  EVM, liveness 3/4). Tetapi **testnet yang bisa diakses internet BELUM
  ADA** — yang kurang: server + IP publik + domain (P1/P2), faucet +
  BlackScan yang live (P5), monitoring + rencana insiden (P6), dan
  keputusan pemilik A/C/D. Status yang benar hari ini: "paket publik
  terbuka, jaringan live masih lokal".
