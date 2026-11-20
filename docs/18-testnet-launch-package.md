# BLACKCHAIN — Paket Peluncuran Testnet Publik (Sesi 8, 2026-11-20)

**Status:** RUNBOOK + DAFTAR PRASYARAT. Rehearsal multi-validator di VM
lokal BERHASIL (`docs/17`), tetapi testnet ini **BELUM PUBLIK** dan
**TIDAK BISA** dijadikan publik hanya dari VM ini. Dokumen ini menjelaskan
cara menjalankan tiap komponen DAN apa yang masih kurang.

## 0. Pernyataan jujur

Yang berjalan hari ini adalah **REHEARSAL**: 4 validator di satu VM,
semua di 127.0.0.1, tanpa IP publik. Siapa pun di luar VM ini TIDAK
BISA terhubung — tidak ada seed node yang bisa di-dial, tidak ada
genesis yang bisa diunduh dari internet (file genesis hanya ada di
repo GitHub sebagai dokumen), tidak ada faucet/BlackScan yang live.
Membuka testnet publik butuh §7 (server + domain + tanggal + pengumuman),
yang semuanya berada di luar kendali agen ini.

## 1. Seed node (untuk publikasi nanti)

Seed node = node CometBFT biasa dengan P2P terbuka (bukan validator:
tanpa kunci validator, tanpa self-stake).

1. Siapkan server (§7) dengan binary `blackchaind-sdk54-bkc` (build
   dari `build/blackchain-sdk54/` — lihat `docs/05-evm-integration.md`).
2. `blackchaind init blackchain-seed --chain-id blackchain_20261120-1
   --home ~/.blackchain`
3. Salin `genesis/blackchain-testnet-genesis.json` (dari repo GitHub
   `BlackchainLabs/blackchain`) ke `~/.blackchain/config/genesis.json`,
   lalu `blackchaind genesis validate --home ~/.blackchain`.
4. Di `config.toml`: `pex = true`, `addr_book_strict = true`
   (default — JANGAN pakai `allow_duplicate_ip = true` /
   `addr_book_strict = false` dari rehearsal; itu khusus 127.0.0.1),
   `persistent_peers` kosong (seed tidak butuh peer tetap),
   `seed_mode = true`.
5. Start: `blackchaind start --home ~/.blackchain
   --minimum-gas-prices 0abkc --p2p.laddr tcp://0.0.0.0:26656
   --rpc.laddr tcp://127.0.0.1:26657` (RPC JANGAN dibuka ke publik).
6. Publikasikan seed address: `<node-id>@<IP-publik>:26656`
   (node-id dari `blackchaind tendermint show-node-id`).

## 2. Validator eksternal bergabung (runbook)

Persyaratan hardware (dari `docs/13` B): min. 8 vCPU / 32 GB RAM /
500 GB NVMe, 1 Gbps, Ubuntu 22.04/24.04. Self-stake: 1.000 BKC
(dari faucet testnet, §3 — validator baru TIDAK mendapat alokasi
genesis; alokasi genesis hanya untuk 4 validator rehearsal §1 yang
kemudian menjadi validator genesis testnet publik bila pemilik
memutuskan demikian — lihat catatan §8).

Langkah:

1. Instal Go 1.24+ dan build binary dari repo (atau unduh rilis resmi
   bila sudah ada — BELUM ADA rilis; saat ini hanya build dari source).
2. `blackchaind init <moniker> --chain-id blackchain_20261120-1`
3. Unduh genesis testnet dari repo GitHub ke `config/genesis.json`,
   `blackchaind genesis validate`.
4. `blackchaind keys add validator --keyring-backend test`
   (SIMPAN mnemonic di tempat aman, offline — ini kunci testnet).
5. Minta 1.000+ tBKC dari faucet (§3) ke alamat validator.
6. `blackchaind genesis gentx validator 1000000000000000000000abkc
   --chain-id blackchain_20261120-1 --keyring-backend test` — gentx
   dikirim ke operator testnet (bukan `collect-gentxs` lokal) untuk
   dimasukkan ke genesis BILA bergabung sebelum genesis final; bila
   bergabung SETELAH testnet berjalan, gunakan `blackchaind tx staking
   create-validator` (transaksi on-chain, butuh faucet + peer aktif).
7. `config.toml`: `seeds = "<seed-node>"`,
   `persistent_peers = "<seed-node>,<validator-lain>"`,
   `laddr` P2P `tcp://0.0.0.0:26656`; buka port 26656 (TCP) di firewall,
   TUTUP port RPC 26657 / EVM 8545 / gRPC 9090 dari internet.
8. Start seperti §1 langkah 5 (tambah flag JSON-RPC bila menjalankan
   node RPC sendiri: `--json-rpc.enable=true --json-rpc.address
   127.0.0.1:8545` — JANGAN bind 0.0.0.0 tanpa reverse proxy + auth).
9. Verifikasi: `curl localhost:26657/status` → `catching_up: false`
   dan height sama dengan seed; `blackchaind query staking validators`.

## 3. Faucet (dari spec `docs/13` A)

- Implementasi BELUM ADA (spec saja). Yang harus dibangun: server web
  kecil (endpoint klaim + CAPTCHA + rate limit per IP) yang memegang
  kunci faucet dan mengirim 100 tBKC/alamat/24 jam dari pool faucet
  (10.000.000 tBKC di genesis — saat ini dipegang alamat operator
  val1 rehearsal; sebelum publik HARUS dipindah ke akun faucet khusus
  / multisig, lihat `docs/17` §2).
- Batas: global 1.000.000 tBKC/hari; bila pool habis, klaim ditolak
  sampai isi ulang lewat proposal gov (community pool).
- Anti-Sybil: CAPTCHA + rate limit IP + (opsional) verifikasi akun
  GitHub/Discord — belum diputuskan pemilik.

## 4. BlackScan (dari spec `docs/11`)

- Implementasi BELUM ADA (spec saja). Yang harus dibangun: Blockscout
  + archive node (node penuh dengan pruning `nothing`, disk 4 TB+
  NVMe) + PostgreSQL 17 + API `/api/v2` + frontend di subdomain
  `scan.<domain>` (§7).
- Archive node HANYA berguna bila di-sync dari genesis testnet final
  (§8) — jangan deploy BlackScan untuk chain rehearsal (chain ini
  akan dibuang saat genesis final dibuat).

## 5. Port & firewall (testnet publik)

| Port | Protokol | Buka ke publik? | Keterangan |
|---|---|---|---|
| 26656 | TCP P2P | YA (validator + seed) | Satu-satunya port konsensus yang wajib publik |
| 26657 | TCP RPC CometBFT | TIDAK (localhost / VPN) | Hanya untuk operator + monitoring |
| 8545 / 8546 | TCP JSON-RPC / WS EVM | TIDAK langsung (via reverse proxy + rate limit) | Node RPC publik memakai proxy |
| 9090 | TCP gRPC | TIDAK | Operator saja |
| 1317 | TCP REST API | TIDAK langsung | Via proxy bila perlu |
| 22 | TCP SSH | TIDAK (VPN / bastion) | Akses server hanya lewat bastion |
| 80 / 443 | TCP HTTP(S) | YA (faucet + BlackScan + website) | Lewat reverse proxy + TLS |

## 6. Monitoring & insiden (belum dibangun)

- Panduan ada (`docs/13` B.4): Prometheus + Grafana + alert bila
  validator miss blok / height tertinggal / disk penuh.
- Rencana insiden & upgrade chain (halt, upgrade height, rollback)
  BELUM DITULIS — wajib sebelum pembukaan publik.
- Snapshot sync / state sync BELUM disiapkan (validator baru harus
  sync dari genesis — lambat bila chain sudah panjang).

## 7. PRASYARAT PUBLIK yang BELUM ADA (tidak bisa dipenuhi dari VM ini)

| # | Prasyarat | Status | Yang harus terjadi |
|---|---|---|---|
| P1 | Server dengan IP publik (min. 1 seed + 1 RPC/archive; idealnya 2–3 server di lokasi berbeda) | BELUM ADA | Pemilik menyewa/menyediakan VPS (spesifikasi `docs/10` §4: seed 4 vCPU/16 GB, validator 16 vCPU/64 GB/NVMe, archive 8–16 vCPU/64 GB/4 TB NVMe) + anggaran hosting bulanan |
| P2 | Domain + DNS (mis. `testnet.blackchain.io`, `scan.*`, `faucet.*`) | BELUM ADA | Pemilik membeli/mengatur domain + DNS + sertifikat TLS |
| P3 | Genesis testnet FINAL + tanggal buka | DRAFT ADA (`docs/17` §2, file `genesis/blackchain-testnet-genesis.json`) | Pemilik memutuskan: (a) apakah 4 alamat validator rehearsal menjadi validator genesis publik, atau genesis dibuat ulang dengan validator lain; (b) tanggal buka testnet; (c) pemindahan pool subsidi+faucet dari alamat operator ke community pool/multisig |
| P4 | Pengumuman resmi testnet | BELUM ADA | Persetujuan eksplisit pemilik (aturan misi) + teks pengumuman + kanal (X/Telegram/Discord/GitHub) |
| P5 | Faucet + BlackScan live | BELUM DIBANGUN | Implementasi dari spec (`docs/11`, `docs/13`) + deploy di P1/P2 |
| P6 | Monitoring, rencana insiden, state sync | BELUM DIBANGUN | Lihat §6 |
| P7 | Alamat vesting (5 multisig + beneficiary + start + Merkle root) | PLACEHOLDER | Wajib diisi pemilik sebelum deploy vesting ke Sepolia (`docs/15` §2); TIDAK menghalangi testnet chain, tetapi menghalangi klaim distribusi |

## 8. Catatan genesis final vs rehearsal

Genesis yang dipakai rehearsal (`genesis/blackchain-testnet-genesis.json`)
adalah DRAFT yang valid dan sudah terbukti menjalankan 4 validator.
Untuk testnet publik ada DUA pilihan (keputusan pemilik):

- **(A) Pakai genesis ini apa adanya** — 4 validator rehearsal menjadi
  validator genesis publik. Cepat, tetapi kunci validator rehearsal
  dibuat di VM ini (keyring `test`) dan TIDAK boleh dipakai untuk
  testnet publik yang serius: kunci harus dibuat ulang di server
  masing-masing validator dengan mnemonic yang dipegang pemiliknya.
- **(B) Buat genesis baru** dengan skrip yang sama
  (`scripts/setup-testnet-4val.sh`) di server publik, dengan validator
  genesis yang kuncinya dibuat di tempat aman. Ini yang
  DIREKOMENDASIKAN. Pool subsidi (20 jt tBKC) + faucet (10 jt tBKC)
  dialokasikan dengan cara yang sama, tetapi ke alamat operator yang
  benar, lalu dipindah ke community pool sebelum pengumuman.

Dalam kedua pilihan, chain rehearsal ini DIBUANG (datanya tidak
dibawa ke testnet publik): height, saldo, dan tx rehearsal tidak
berlanjut — yang dibawa hanyalah genesis, skrip, dan pelajaran
(F32/F33).
