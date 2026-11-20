# 08 — Benchmark Harness EVM (TPS) — BLACKCHAIN devnet

> Status: **harness selesai dan teruji ujung-ke-ujung di devnet live** (mode
> `contract`, 20/20 sukses). Mode `transfers` **menunggu pendanaan akun tes**
> — lihat "Yang masih perlu dijalankan". Semua angka di bawah adalah hasil
> pengukuran nyata di devnet, bukan estimasi. Tidak ada angka yang dikarang.

## 1. File

| File | Isi |
|---|---|
| `scripts/bench-evm.py` | Harness benchmark (Python, stdlib + `eth_account` 0.14.0) |
| `~/workspace/.build-tmp/bench-addrs.json` | Alamat 2 akun tes (boleh dibaca induk) |
| `~/workspace/.build-tmp/bench-keys.json` | Private key 2 akun tes, mode `0600` — **JANGAN** dipindah ke `blackchain/`, jangan di-commit, jangan dicetak |
| `~/workspace/.build-tmp/bench-contract-20.json` | Hasil JSON mentah uji contract 20 calls |

## 2. Dependensi

- Python venv `~/workspace/.build-tmp/evmtest-venv/bin/python` dengan
  `eth_account==0.14.0` (plus `eth-utils`, `eth-hash`, dsb. — sudah
  terinstal). **Tidak butuh `web3`**: JSON-RPC dilakukan dengan `urllib`
  stdlib, mengikuti pola `~/workspace/.build-tmp/evm-transfer-test.py`.
- Kontrak `SimpleCounter` dikompilasi dengan **solc 0.8.28 via solc-js**
  (`npm install solc@0.8.28`, source di `/tmp/solcjs/SimpleCounter.sol`).
  Bytecode hasil kompilasi di-embed sebagai konstanta di `bench-evm.py`
  beserta source Solidity-nya di docstring, jadi harness tidak butuh `solc`
  saat jalan.
- Devnet harus live (JSON-RPC + CometBFT RPC dapat dijangkau).

## 3. Cara pakai

Semua mode **wajib** diberi `--rpc` dan `--chain-id` (tidak ada default —
sengaja, agar harness yang sama jalan di devnet lama maupun devnet
identitas baru tanpa edit kode). `--comet-rpc` opsional; bila tidak diberi,
info tinggi CometBFT dilaporkan sebagai tidak tersedia, bukan dikarang.

Interpreter selalu venv di atas, mis.:

```bash
PY=~/workspace/.build-tmp/evmtest-venv/bin/python
H=~/workspace/blackchain/scripts/bench-evm.py
```

### 3.1 `generate` — buat akun tes fresh

```bash
$PY $H --mode generate --accounts 2 \
  --addrs-out ~/workspace/.build-tmp/bench-addrs.json \
  --keys-out ~/workspace/.build-tmp/bench-keys.json
```

Mencetak alamat ke stdout dan ke `--addrs-out`. Private key **hanya**
ditulis ke `--keys-out` (mode `0600`) dan **tidak pernah dicetak**.

### 3.2 `fund` — danai akun tes dari validator (dijalankan induk)

```bash
PK_HEX='<kunci-validator>' $PY $H --mode fund \
  --rpc http://127.0.0.1:8545 --chain-id 262144 \
  --addrs ~/workspace/.build-tmp/bench-addrs.json \
  --txs-per-account 10 --fund-mode transfers
```

- `PK_HEX` dibaca dari environment saja, **tidak pernah dicetak**,
  tidak ditulis ke disk.
- Jumlah per akun dihitung dari `eth_gasPrice` live + beban rencana
  (`--txs-per-account`, `--value`, `--fund-mode`): untuk transfers
  `txs × (value + 21000 × gasPrice) × 1,2 + 10.000 wei`; untuk contract
  `(500.000 + txs × 100.000) × gasPrice × 1,2 + 10.000 wei`.
  `--fund-amount` (wei/akun) meng-override hitungan ini.
- Menolak jalan bila `eth_chainId` ≠ `--chain-id`, bila `PK_HEX` kosong,
  atau bila saldo funder tidak cukup (dicek dulu; tidak ada tx yang
  terkirim dalam kondisi itu). Mencetak per alamat: jumlah, tx hash,
  status receipt.

### 3.3 `transfers` — N akun × M transfer 1 wei (self-transfer, paralel)

```bash
$PY $H --mode transfers --rpc http://127.0.0.1:8545 --chain-id 262144 \
  --comet-rpc http://127.0.0.1:26667 \
  --accounts 2 --txs-per-account 10 \
  --keys ~/workspace/.build-tmp/bench-keys.json \
  --out ~/workspace/.build-tmp/bench-transfers-2x10.json
```

Tiap akun mengirim ke alamatnya sendiri (self-transfer) agar dana tidak
hilang ke alamat buangan; nonce dikelola per akun; `gasPrice` diambil dari
`eth_gasPrice` live. Bila saldo akun tidak cukup untuk bebannya, harness
**fail-fast sebelum mengirim apa pun**.

### 3.4 `contract` — deploy SimpleCounter + N `increment()` paralel

```bash
$PY $H --mode contract --rpc http://127.0.0.1:8545 --chain-id 262144 \
  --comet-rpc http://127.0.0.1:26667 --calls 20 \
  --keys ~/workspace/.build-tmp/bench-keys.json \
  --out ~/workspace/.build-tmp/bench-contract-20.json
```

Deploy dari akun pertama di file keys; gas deploy & gas `increment()`
diestimasi via `eth_estimateGas` (fallback 500.000 / 100.000 bila estimasi
gagal). Setelah semua panggilan, harness membaca `counter()` via
`eth_call` dan memeriksa nilainya sama dengan jumlah increment yang
sukses.

## 4. Metrik yang diukur (kedua mode beban)

- `tx planned / submitted / success`, `tx failed (submit)`,
  `tx failed (receipt/timeout)` — gagal dihitung, tidak disembunyikan;
  20 error pertama dicantumkan di output.
- `duration total (s)`, `TPS sustained` = tx sukses / durasi jendela
  (submit pertama → receipt terakhir), `TPS submitted`.
- Latensi submit→receipt: p50 / p95 / maks / mean.
- Blok: `block_before → block_after`, jumlah tx per blok dan rata-rata
  block time dari `eth_getBlockByNumber` (maks. 500 blok), plus tinggi
  CometBFT sebelum/sesudah dari `--comet-rpc` sebagai cross-check.
- Mode contract tambahan: tx hash + latensi deploy, `gasUsed` deploy,
  alamat kontrak, `counter()` akhir dan apakah cocok dengan sukses.
- Output: tabel markdown di stdout + JSON lengkap ke `--out` (bila
  diberi). Exit code 1 bila ada tx yang gagal.

## 5. Hasil pengukuran nyata

### 5.1 Lingkungan saat pengukuran (20 Nov 2026, ~22:03–22:04 WIB)

- Devnet: Cosmos SDK v0.54.5 + Cosmos EVM v0.7.4, 1 validator,
  `chainId` 262144 (`0x40000`), JSON-RPC `http://127.0.0.1:8545`,
  CometBFT RPC `http://127.0.0.1:26667`, denom `stake` (1 stake = 1 wei).
- `eth_gasPrice` saat itu: **0 wei**. `gasLimit` blok terakhir:
  `0xffffffff` (4.294.967.295). Saldo alamat miner blok
  (`0x1a5c9b17968b36730036a8678c1a75cc64f1938f`): **900.000.000 wei**
  (diukur via `eth_getBalance`).

### 5.2 Mode `contract` — 20 × `increment()` (BERHASIL)

Perintah (persis seperti §3.4, `--calls 20`):

| metrik | nilai terukur |
|---|---|
| tx planned / submitted / success | 20 / 20 / 20 |
| tx gagal (submit / receipt) | 0 / 0 |
| durasi total | 6,552 dtk |
| **TPS sustained (sukses / jendela)** | **3,053** |
| TPS submitted | 122,998 (semua tx terkirim dalam 0,163 dtk) |
| latensi submit→receipt p50 | 6,452 dtk |
| latensi submit→receipt p95 | 6,501 dtk |
| latensi submit→receipt maks | 6,503 dtk |
| latensi mean | 6,45 dtk |
| blok | 1001 → 1002 (2 blok, 21 tx dalam rentang) |
| tx per blok | [1, 20] — ke-20 increment mendarat dalam **satu blok** (1002) |
| rata-rata block time teramati | 5,0 dtk |
| tinggi CometBFT | 1001 → 1002 (cocok dengan nomor blok EVM) |
| deploy SimpleCounter | 6,368 dtk; tx `0x2e01fb5ec0807617ee20b39eb651022726777888cbc5c0cc338b60f68232dc9d`; gasUsed **118.643**; gas estimasi ×1,2 = 152.371; alamat kontrak `0x79410D958f51AeF76733f2664A1a9a6121F4A029`; code 303 byte |
| gas `increment()` (estimasi ×1,2) | 62.220 |
| `counter()` akhir | **20** (cocok dengan 20 sukses — `counter_matches_success: true`) |

**Interpretasi jujur:** angka TPS 3,053 pada beban sekecil ini **bukan
batas throughput chain** — ini artefak jendela: semua 20 tx terkirim
dalam 0,16 dtk lalu menunggu blok berikutnya (~5 dtk block time), dan
semuanya masuk dalam satu blok. Latensi ~6,5 dtk juga didominasi waktu
tunggu blok, bukan eksekusi. Yang terbukti di sini: harness jalan
ujung-ke-ujung (deploy → 20 call paralel → receipt → verifikasi counter),
nonce paralel satu akun bekerja, dan chain menampung 20 tx kontrak dalam
satu blok. Untuk angka TPS maksimum yang bermakna, perlu beban lebih
besar (ratusan–ribuan tx, beberapa akun) — lihat §7.

Karena `gasPrice = 0`, deploy + 20 increment ini **tidak butuh dana**:
saldo deployer `0x17371f2fceCC8907e6cB9F37213A4b38bF3F5F16` tetap 0 wei
sebelum dan sesudah uji.

### 5.3 Mode `transfers` — 2 akun × 10 transfer (BELUM BERJALAN)

Percobaan dry-run tanpa dana berakhir fail-fast sesuai desain (tidak ada
tx terkirim, exit 1):

```
ERROR: 0x17371f2fceCC8907e6cB9F37213A4b38bF3F5F16 balance 0 wei < needed
10 wei for 10 txs. Fund it first (bench-evm.py --mode fund).
Aborting; nothing sent.
```

Belum ada angka TPS/latensi transfers — menunggu pendanaan (§7).
**UPDATE Sesi 4 (2026-11-20): transfers SUDAH BERJALAN di devnet identitas
BKC (chain 20261120, RPC 8555).** Hasil lengkap di `docs/09-benchmark-tps.md`:
iterasi 1 (blok 5 dtk) 66,29 TPS sustained / 1000 tx; iterasi 2 (blok 1 dtk)
82,08 TPS; iterasi 3 (blok 0,5 dtk) 87,31 TPS; iterasi 4 (semua timeout
500ms) 87,50 TPS — plateau. Contract 500 calls: 57,15 → 80,91 → 89,24 →
88,68 TPS. **Maksimum terukur: ~89 TPS sustained (finalized).**

## 6. Temuan saat membangun harness (bug nyata, sudah diperbaiki)

1. **Alamat dari Cosmos EVM tidak selalu EIP-55 checksum.** Receipt
   `contractAddress` pertama (`0xd0be475cb4e1a7f2295c3082d7ee002384fd5e28`,
   deploy tx `0x7705b424ad1784a38487e00c98fc791aafd192f9f6925259acabb93f8179e576`,
   gasUsed 118.643) lolos `is_address` tapi gagal `is_checksum_address`,
   sehingga `eth_account.sign_transaction` menolak semua 20
   `increment()` dengan `TypeError: Transaction had invalid fields:
   {'to': ...}`. Perbaikan: semua alamat `to` dinormalisasi dengan
   `eth_utils.to_checksum_address` (fund, transfers, contract). Setelah
   perbaikan, uji §5.2 berhasil 20/20. Kontrak yatim pertama (counter 0)
   tetap ada di chain; tidak dipakai lagi.
2. **`eth_coinbase` tidak tersedia** di node ini (`-32601 method does not
   exist`); alamat miner diambil dari field `miner` blok terakhir.
3. **Fail-fast tanpa dana bekerja** untuk transfers (saldo 0 < 10 wei)
   dan untuk contract bila `gasPrice > 0`. Bila `gasPrice = 0`, beban
   dengan `value = 0` memang gratis — itu perilaku chain, bukan bug
   harness; pre-flight tetap menghitung kebutuhan dari `gasPrice` live.

## 7. Yang masih perlu dijalankan

### 7.1 Pendanaan akun tes (oleh induk) — untuk uji transfers kecil

Akun (file `~/workspace/.build-tmp/bench-addrs.json`):

| alamat | kebutuhan |
|---|---|
| `0x17371f2fceCC8907e6cB9F37213A4b38bF3F5F16` | 10.012 wei |
| `0xf1Fdbaa6812a440d5F6DD15ef72f87Ddd4dA5667` | 10.012 wei |

Hitungan: 10 tx × (1 wei value + 21.000 × 0 gasPrice) × 1,2 + 10.000
wei buffer = **10.012 wei per akun**, total **20.024 wei** — tidak ada
artinya dibanding saldo validator/miner 900.000.000 wei. Perintah fund
(lihat §3.2) menghitung ulang jumlah ini sendiri dari `gasPrice` live;
`--fund-amount` tidak diperlukan.

### 7.2 Setelah dana masuk — uji transfers kecil

```bash
$PY $H --mode transfers --rpc http://127.0.0.1:8545 --chain-id 262144 \
  --comet-rpc http://127.0.0.1:26667 \
  --accounts 2 --txs-per-account 10 \
  --keys ~/workspace/.build-tmp/bench-keys.json \
  --out ~/workspace/.build-tmp/bench-transfers-2x10.json
```

Lalu catat TPS/latensi ke §5.3 dokumen ini.

### 7.3 Di devnet identitas baru (chain ID 20261120, denom `abkc`, JSON-RPC 8555)

- Buat akun fresh baru (`--mode generate` dengan file output baru) —
  jangan pakai ulang akun devnet lama.
- Jalankan fund + transfers + contract dengan argumen baru, mis.:

```bash
$PY $H --mode fund --rpc http://127.0.0.1:8555 --chain-id 20261120 \
  --addrs <addrs-baru>.json --txs-per-account 10 --fund-mode transfers
$PY $H --mode transfers --rpc http://127.0.0.1:8555 --chain-id 20261120 \
  --comet-rpc <comet-rpc-baru> --accounts 2 --txs-per-account 10 \
  --keys <keys-baru>.json --out <hasil>.json
$PY $H --mode contract --rpc http://127.0.0.1:8555 --chain-id 20261120 \
  --comet-rpc <comet-rpc-baru> --calls 20 \
  --keys <keys-baru>.json --out <hasil>.json
```

- Perlu dicek ulang di devnet baru: `eth_gasPrice` (bila bukan 0,
  kebutuhan dana berubah dan dihitung otomatis oleh `--mode fund`),
  `gasLimit` blok, dan block time. **Tidak ada perubahan kode harness
  yang diperlukan** — semua parameter lewat argumen; grep memastikan
  tidak ada `262144` / `8545` / `26667` yang ter-hardcode di script.
- Beban lebih besar (mis. 10 akun × 100 transfer, 500–1000 increment)
  dianjurkan untuk mengukur TPS sustained yang bermakna; beban kecil
  di atas hanya membuktikan harness jalan.

## 8. Batasan yang diketahui

- **Block time ~5 dtk mendominasi latensi** pada beban kecil; TPS
  sustained beban kecil ≈ `N_tx / block_time`, bukan batas chain.
- **Block gas limit teramati sangat besar** (`0xffffffff`) — bukan
  batas praktis; batas nyata kemungkinan di mempool / CometBFT
  (`mempool_size`, timeout commit) dan belum diukur.
- **Mempool belum diprobing:** harness tidak mengukur antrean mempool,
  rejeksi `tx pool full`, atau perilaku saat tx melebihi satu blok.
- **Satu node, satu validator:** hasil tidak menggambarkan jaringan
  multi-validator (latensi konsensus, gossip).
- **Nonce paralel satu akun** (mode contract) memakai lock di proses;
  menjalankan dua proses bench bersamaan dengan akun yang sama akan
  tabrakan nonce — gunakan akun berbeda per proses.
- **Receipt polling** tiap 0,25 dtk; latensi di bawah ~0,25 dtk tidak
  ter-resolusi halus (tidak relevan selama block time 5 dtk).
- Statistik blok dibatasi 500 blok terakhir bila rentang lebih besar.
- Harness memakai legacy tx (`gasPrice`, tanpa EIP-1559) — sesuai yang
  dipakai transfer test sebelumnya dan diterima Cosmos EVM v0.7.4.
- Keamanan: kunci tes hanya di `~/workspace/.build-tmp/bench-keys.json`
  (0600). Jangan commit file itu; jangan salin ke `blackchain/`.
  Kunci validator tidak pernah dipegang harness — hanya via `PK_HEX`
  saat `--mode fund`.
