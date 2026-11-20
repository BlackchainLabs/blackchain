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
**Sesi 12 (21 Nov 2026 00:35 WIB / 20 Nov 17:35 UTC):** faucet
(`repo/faucet/`, 100 tBKC/klaim, uji end-to-end LOLOS), BlackScan Lite
(`repo/blackscan/`, 913 blok ter-index, lag 0) dan monitoring +
rencana insiden (`repo/monitoring/health-check.py` + `docs/24`) SELESAI
dan JALAN melawan rehearsal lokal — semuanya lokal (127.0.0.1).
Rehearsal 4 validator terakhir terverifikasi 20 Nov 17:35 UTC
(height 923, hash `2531A37A…` sama di keempat node, `catching_up: false`,
masing-masing 3 peer). Devnet BKC height 11.359. **Insiden F34:**
semua proses sempat mati total akibat restart VM/runtime
(20 Nov ~17:28 UTC) dan dipulihkan Sesi 12 tanpa regenesis
(`scripts/restart-local-nodes.sh`) — lihat `docs/23` §5 dan `docs/24` §3.5.
**Sesi 9 SELESAI (21 Nov 2026 ~02:00 WIB):** implementasi kode Fase 1
(ingest paralel) SELESAI + TERUKUR — `eth_sendRawTransactionBatch`
live di fork devnet (chain 20261120), uji fungsional LOLOS, E1/E2
terukur di VM 1,5 CPU: transfers 61,2 → **87,3 TPS (+43%)**, submit
95 → 204 tx/dtk (1.301 tx/dtk mentah), contract sustained TETAP
~49 TPS (bottleneck blok/eksekusi serial, bukan ingest) — lihat
`docs/19`. Fork TIDAK masuk testnet (masih di `build/` + devnet
terpisah); merge ke pohon Jalur A menunggu keputusan pemilik.

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
| Jalur ke 100.000 TPS | 🔄 Dikerjakan | Riset & desain selesai (`docs/10`); urutan Fase 1→4 DISETUJUI Sesi 7; desain implementasi Fase 1 selesai (`docs/16`); **implementasi kode Fase 1 SELESAI + TERUKUR Sesi 9** (`docs/19`, fork `build/blackchain-phase1/`, endpoint `eth_sendRawTransactionBatch` live di devnet fork chain 20261120): transfers 61,2 → 87,3 TPS (+43%), submit 95 → 204 tx/dtk (1.301 mentah), contract sustained tetap ~49 TPS (bottleneck blok/eksekusi serial). **Yang belum:** merge fork ke pohon Jalur A (butuh keputusan pemilik), Fase 1b (shard txpool internal), Fase 2–4, dan E1/E2 di hardware layak (blokir B). Plafon terukur tahap 1 di VM ini: ~87 TPS transfer / ~49 TPS contract — BUKAN 300–1.000 TPS (itu estimasi lama, kini diganti angka terukur). |
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
| BlackScan (explorer) | ✅ Siap (Lite) | **Sesi 12: BlackScan Lite JALAN** (`repo/blackscan/`, `docs/23`) — indexer SQLite + UI + API `/api/v2`, 913 blok ter-index, lag 0, tx Sesi 8 (blok 6) + tx faucet (blok 829) tampil benar. **BUKAN Blockscout penuh** (butuh Elixir + PostgreSQL + archive node — keputusan pemilik, `docs/23` §7) |
| BlackSwap (DEX AMM) | 🔄 Dikerjakan | Spesifikasi v0.1 selesai (`docs/12`); kontrak, test & audit BELUM |
| Faucet testnet | ✅ Siap (minimal) | **Sesi 12: faucet JALAN** (`repo/faucet/`, `docs/22`) — 100 tBKC/klaim, PoW ringan (bukan hCaptcha), cooldown 24 jam; uji end-to-end LOLOS (tx `0x8dfe2e3c…`, blok 829, +100 tBKC; klaim ke-2 ditolak). Kapasitas efektif ~99 klaim dari saldo cair 9.899,9999 BKC — pool faucet 10 jt tBKC di genesis berstatus STAKED, bukan cair (butuh keputusan pemilik untuk isi ulang) |
| Black Wallet | ⬜ Belum | Spesifikasi di whitepaper Bab 14; belum ada spec v0.1 |
| BlackBridge | ⬜ Belum | Desain keamanan di whitepaper Bab 16; TIDAK diluncurkan tanpa audit |
| Panduan validator | ✅ Siap (dokumen) | `docs/13` B + `VALIDATOR_GUIDE.md` |

## 4. Operasional testnet

| Item | Status | Bukti / catatan |
|---|---|---|
| Repo GitHub publik | ✅ Siap | `BlackchainLabs/blackchain`, remote head `b945142f` (Sesi 11); lokal head `24d5ad1` |
| Roadmap diperbarui | ✅ Siap | `ROADMAP.md` (status 21 Nov 2026 00:35 WIB, Sesi 12) |
| Seed / peer testnet | 🔄 Dikerjakan | **Paket publik TERBUKA Sesi 10** (`repo/testnet/`: genesis + README + `seeds.md`); daftar seed berisi node ID + alamat 127.0.0.1 rehearsal — seed PUBLIK belum ada (butuh server + IP publik, prasyarat P1). **Sesi 11 (21 Nov 2026): paket deploy VPS SIAP — persiapan, BUKAN selesai** (`repo/testnet/vps-deploy.sh` + `vps-runbook.md` + `docs/21`); VPS sudah disediakan pemilik, tetapi IP/username/OS/konfirmasi kunci SSH belum diterima dan deploy belum dieksekusi — P1 menjadi SEBAGIAN (lihat `docs/21` §6). **Sesi 12: IP publik diterima (103.147.8.20, Starnet Bandung) tetapi SSH GAGAL — port 22/80/443 tidak menjawab** (kemungkinan VPS belum menyala / firewall menutup port 22); deploy tertahan sampai pemilik memeriksa status + firewall VPS (lihat `docs/21` dan laporan Sesi 11) |
| Monitoring & alert validator | ✅ Siap (lokal) | **Sesi 12: health-check JALAN** (`repo/monitoring/health-check.py` + `docs/24`) — cek height/hash/fork/halt/faucet/BlackScan, tulis `data/status.json`, exit 0/1/2; uji 2x LOLOS (OK, 0 masalah). Cron tiap menit BELUM dipasang (dipasang Muse utama); alerting keluar (Telegram/email) BELUM ada |
| Snapshot sync / state sync | ⬜ Belum | Belum disiapkan |
| Rencana insiden & upgrade | ✅ Siap | **Sesi 12: `docs/24-monitoring-incident.md`** — runbook halt, fork, validator down, seed down, restart VM (F34), faucet habis, BlackScan lag; pemilik tiap langkah dicatat |
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
| B | **Anggaran hardware** — siapa menyediakan & membayar server validator tahap 1 (16 vCPU/64 GB/NVMe) + node RPC/archive | E1/E2 Fase 1 SUDAH dijalankan di VM 1,5 CPU (perbandingan relatif, `docs/19`) — yang masih tertahan: angka ABSOLUT di hardware layak + node RPC khusus + merge fork ke testnet | `docs/10` §4, `docs/16` §5.1, `docs/19` §5–§6 |
| B2 | **Akses VPS seed** (bagian dari B) — VPS sudah disediakan pemilik 21 Nov 2026, IP publik **103.147.8.20** (Starnet, Bandung) diterima 00:14 WIB, tetapi **SSH GAGAL dari VM ini: port 22/80/443 tidak menjawab** (kemungkinan VPS belum menyala / firewall menutup port 22 / layanan SSH belum aktif); deploy seed belum dieksekusi | Tidak ada endpoint publik sampai VPS bisa diakses + deploy + verifikasi selesai (runbook §3–§5) | `docs/21`, `repo/testnet/vps-runbook.md` §1 |
| C | **Genesis testnet final + tanggal buka** — draft genesis SUDAH ADA dan teruji (`docs/17` §2, `genesis/blackchain-testnet-genesis.json`); yang tersisa: keputusan pakai-apa-adanya vs buat-ulang, pemindahan pool subsidi (20 jt tBKC) + faucet (10 jt tBKC) dari alamat operator ke community pool/multisig, dan tanggal buka testnet | Testnet tidak bisa dibuka | `docs/18` §7–§8 |
| D | **Pengumuman resmi testnet** | Butuh persetujuan eksplisit pemilik (aturan misi) | — |

**Aturan yang tetap berlaku:** ketiga keputusan desain di atas diputuskan
oleh pemilik lewat Muse utama, bukan oleh AI. Testnet publik TIDAK
dibuka sebelum blokir A dan C selesai; blokir B tidak menghalangi
testnet (bisa dibuka dengan plafon ~89 TPS yang jujur) tetapi
menghalangi pekerjaan performa Fase 1.

## 6. Ringkasan kesiapan (revisi Sesi 12)

- **Siap:** 18 item · **Dikerjakan/sebagian:** 6 item ·
  **Belum dimulai:** 5 item · **Diblokir komunikasi:** 0 item (draft
  pengumuman sudah ada, menunggu persetujuan) · **Blokir konkret
  pemilik:** 4 item (A alamat vesting, B anggaran hardware/server+domain,
  C keputusan genesis final + tanggal buka, D persetujuan pengumuman).
  (Koreksi hitung: total 29 item — ringkasan lama menulis 7 "sebagian"
  padahal 8; Sesi 12 memindahkan 4 item ke Siap: BlackScan, Faucet,
  Monitoring, Rencana insiden.)
  **Sesi 12 (21 Nov 2026 00:35 WIB):** faucet + BlackScan Lite +
  monitoring/insiden SELESAI dan JALAN (lokal); hitungan berubah
  14/8/7 → **18/6/5**. P1 tetap SEBAGIAN (IP VPS diterima tetapi SSH
  gagal — lihat B2).
  **Sesi 9 SELESAI (21 Nov 2026 ~02:00 WIB):** Fase 1 (ingest paralel)
  terimplementasi + terukur (`docs/19`); hitungan TIDAK berubah
  (baris "Jalur ke 100.000 TPS" tetap Dikerjakan — Fase 1b + Fase 2–4
  + merge fork masih menunggu).
- **Kesimpulan jujur:** **paket testnet publik TERBUKA** (genesis +
  panduan + seed list jujur + draft pengumuman), chain-nya SUDAH
  TERBUKTI BERJALAN (rehearsal 4 validator: sinkron height 923,
  transfer EVM, liveness 3/4), dan **faucet + BlackScan + monitoring
  kini JALAN melawan rehearsal lokal**. Tetapi **testnet yang bisa
  diakses internet BELUM ADA** — yang kurang: akses VPS + deploy seed
  (B2), domain (P2), keputusan pemilik A/C/D, dan BlackSwap.
  Status yang benar hari ini: "paket publik terbuka, layanan testnet
  jalan lokal, jaringan live masih lokal".
