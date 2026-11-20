# BLACKCHAIN — Spesifikasi BlackScan (Explorer Testnet) v0.1 (Sesi 6, 2026-11-20)

**Status:** SPESIFIKASI — belum ada kode, belum ada deploy. Keputusan
implementasi mengikuti dokumen ini; angka infra adalah kebutuhan
rencana, bukan hasil ukur.

## 1. Keputusan dasar

| Keputusan | Pilihan | Alasan |
|---|---|---|
| Software explorer | **Blockscout** (open source, EVM) | Diputuskan di `docs/02` §5; dipakai >1.000 jaringan EVM; menyediakan indexer + API + frontend dalam satu paket; mendukung verifikasi kontrak Foundry/Hardhat. |
| Sumber data | Archive node BLACKCHAIN (JSON-RPC + tracing) | Indexer butuh state historis + trace internal; node pruned TIDAK cukup. |
| Database | PostgreSQL 17+ | Standar Blockscout; beban tulis append-only saat indexing, baca-berat dari API. |
| API publik | Blockscout REST `/api/v2` + API gaya Etherscan `/api?module=...&action=...` | `/api/v2` untuk frontend & dApp; kompatibilitas Etherscan untuk tooling yang sudah ada (MetaMask, Hardhat, Foundry). |
| Nama & domain | `BlackScan`, domain testnet diputuskan pemilik | — |

**Catatan lisensi:** lisensi Blockscout berubah dari GPL-3.0 ke
source-available pada April 2026 — periksa ketentuan lisensi yang
berlaku saat deploy bila explorer dipakai komersial.

## 2. Arsitektur

```
Pengguna / dApp / wallet
        │  HTTPS
        ▼
┌─────────────────────────────┐
│ Frontend (Next.js/TS)       │  ← memanggil API yang sama dengan publik
└──────────────┬──────────────┘
               │
┌──────────────┴──────────────┐
│ API (Elixir/Phoenix)        │  /api/v2 + /api (Etherscan-style)
│  + microservices (Rust)     │  verifikasi kontrak, stats, name service
└──────────────┬──────────────┘
               │
┌──────────────┴──────────────┐
│ PostgreSQL 17+              │  blok, tx, receipt, trace, log, token,
│  (indexer DB)               │  saldo, kontrak terverifikasi
└──────────────┬──────────────┘
               │
┌──────────────┴──────────────┐
│ Indexer (Elixir, GenServer) │  fetchers: block realtime + catch-up,
│  + Redis (opsional)         │  pending tx, token, internal tx
└──────────────┬──────────────┘
               │  JSON-RPC + WebSocket
┌──────────────┴──────────────┐
│ Archive node BLACKCHAIN     │  pruning = nothing (archive),
│  (blackchaind + EVM RPC)    │  tracing aktif (debug_trace*),
│                             │  eth_getBlockReceipts tersedia
└─────────────────────────────┘
```

**Reorg:** CometBFT memiliki finalitas instan (tidak ada fork setelah
commit) — indexer tidak perlu menangani reorg dalam seperti di
Ethereum PoW/PoS; tetap implementasikan penanganan standar Blockscout
untuk keamanan.

## 3. Fitur

### MVP (wajib untuk testnet publik)

- [ ] Halaman blok: daftar blok, detail blok (hash, height, waktu,
      proposer, jumlah tx, gas used, app-hash).
- [ ] Halaman transaksi: detail tx (status, blok, pengirim/penerima,
      nilai, gas, input ter-decode bila kontrak terverifikasi, log/event).
- [ ] Halaman alamat: saldo BKC, daftar tx, token yang dimiliki.
- [ ] Pencarian: berdasarkan hash tx, alamat, nomor blok, nama token.
- [ ] Token: daftar transfer token ERC-20 (BKC + token testnet lain),
      holder.
- [ ] Kontrak: tampilkan bytecode + verifikasi source (Foundry/Hardhat/
      Remix) — WAJIB untuk kontrak vesting/claim sebelum diumumkan.
- [ ] Statistik: TPS harian, jumlah tx, jumlah blok, waktu blok
      rata-rata, jumlah alamat aktif.
- [ ] API publik dengan rate limit (lihat §5).

### Fase 2 (setelah testnet stabil)

- [ ] Internal transaction (trace) lengkap.
- [ ] Halaman validator: set aktif, voting power, uptime, komisi,
      riwayat slash (data dari modul staking/slashing via gRPC/REST
      Cosmos — BUKAN dari EVM RPC).
- [ ] Token NFT (ERC-721/1155) bila ada.
- [ ] Grafik: gas price, ukuran blok, pertumbuhan alamat.
- [ ] Layanan nama (opsional).

### TIDAK termasuk

- Faucet (lihat `docs/13` — layanan terpisah).
- Swap/trading (lihat `docs/12`).
- Bridge (modul terpisah, butuh audit).

## 4. Sumber data per fitur (RPC / Indexer)

| Data | Sumber | Metode / catatan |
|---|---|---|
| Blok + tx | Archive node JSON-RPC | `eth_getBlockByNumber` (full tx), `eth_getBlockReceipts` (satu call per blok, lebih murah dari per-tx receipt) |
| Receipt & status | Archive node | `eth_getTransactionReceipt` / `eth_getBlockReceipts` |
| Log/event | Archive node | `eth_getLogs` untuk backfill range historis |
| Trace internal | Archive node (tracing aktif) | `debug_traceTransaction` / `debug_traceBlockByNumber` — butuh node dengan tracing; indexer batch agar tidak membebani RPC |
| Saldo & state | Archive node | `eth_getBalance`, `eth_call` (hati-hati: panggil read-only, batasi) |
| Data validator | Cosmos gRPC/REST node | `/cosmos/staking/v1beta1/validators`, `/cosmos/slashing/v1beta1/...` — endpoint Cosmos, bukan EVM |
| Blok baru realtime | WebSocket node | `eth_subscribe newHeads` atau polling `eth_blockNumber` (Blockscout realtime fetcher memakai WS + polling fallback) |

**Kebutuhan node:** archive node WAJIB `pruning = "nothing"` dan
tracing aktif; node validator TIDAK BOLEH dipakai sebagai sumber
indexer (bebani konsensus). Sediakan minimal 1 node RPC khusus untuk
BlackScan + 1 cadangan.

## 5. Endpoint API (yang diekspos publik)

Semua di bawah mengikuti pola Blockscout v7 (`/api/v2` REST + `/api`
gaya Etherscan). Rate limit awal: **5 req/detik per IP** (dapat diubah
setelah melihat beban).

| Endpoint | Fungsi |
|---|---|
| `GET /api/v2/blocks` | Daftar blok terbaru (paginasi) |
| `GET /api/v2/blocks/:height_or_hash` | Detail blok |
| `GET /api/v2/transactions` | Daftar tx terbaru |
| `GET /api/v2/transactions/:hash` | Detail tx + log |
| `GET /api/v2/addresses/:address` | Info alamat + saldo |
| `GET /api/v2/addresses/:address/transactions` | Riwayat tx alamat |
| `GET /api/v2/addresses/:address/token-transfers` | Transfer token alamat |
| `GET /api/v2/tokens/:address` | Info token |
| `GET /api/v2/tokens/:address/holders` | Holder token |
| `GET /api/v2/smart-contracts/:address` | Info + source terverifikasi |
| `GET /api/v2/stats` | Statistik chain (TPS, tx count, dsb.) |
| `GET /api/v2/search?q=...` | Pencarian |
| `GET /api/health` | Health check indexer + DB |
| `GET /api?module=account&action=balance&address=...` | Kompatibilitas Etherscan |
| `GET /api?module=account&action=txlist&address=...` | Kompatibilitas Etherscan |
| `POST /api/v2/smart-contracts/:address/verification` | Submit verifikasi kontrak |

## 6. Infrastruktur (rencana)

| Komponen | Spesifikasi minimum (rencana) | Catatan |
|---|---|---|
| Archive node | 8–16 vCPU, 32–64 GB RAM, NVMe ≥2 TB | Disk tumbuh seiring chain; pantau tiap minggu |
| PostgreSQL | 4–8 vCPU, 16–32 GB RAM, NVMe ≥500 GB | Backup harian; indeks pada (block_number, tx_hash, address) |
| Indexer + API | 4 vCPU, 8 GB RAM | Stateless (bisa 2 replika di belakang LB) |
| Frontend | 2 vCPU, 4 GB RAM (atau static hosting + CDN) | — |
| Redis (opsional) | 1 GB | Cache + queue indexer |
| Total awal | ~4 layanan | Semua di Docker Compose dulu; Kubernetes bila trafik naik |

**Backfill:** saat pertama dinyalakan, indexer mengejar dari blok
genesis testnet sampai head (catch-up fetcher). Pada ~89 TPS, satu hari
≈ 7,7 juta tx — backfill awal diperkirakan berjam-jam; ukur nyata saat
deploy testnet dan catat.

## 7. Kriteria penerimaan (sebelum diumumkan ke publik)

1. Indexer mengejar head dalam <60 detik dari blok terbaru (lag index).
2. Semua tx devnet (transfer + contract call Sesi 4) tampil benar di UI.
3. Kontrak BKC/TeamVesting/CommunityClaim terverifikasi dan tampil
   source-nya.
4. API `/api/v2/stats` mengembalikan angka yang cocok dengan node
   (jumlah blok, jumlah tx).
5. Health endpoint hijau 24 jam berturut-turut di devnet.
6. Rate limit terbukti menahan flood sederhana (uji beban ringan).

## 8. Hal terbuka (butuh keputusan pemilik)

- Domain + hosting (server sendiri / cloud, siapa yang membayar).
- Apakah BlackScan testnet boleh menampilkan alamat/label validator
  (privasi operator).
- Retensi data: berapa lama log penuh disimpan; kapan arsip dipangkas.
