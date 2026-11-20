# BLACKCHAIN — Implementasi Fase 1: Ingest Paralel (Sesi 9, 2026-11-20)

**Status:** IMPLEMENTASI SELESAI (kode) + PENGUKURAN E1/E2 — lihat §5.
Desain yang diimplementasikan: `docs/16-phase1-ingest-design.md`.
Semua angka di dokumen ini berasal dari pengukuran nyata di VM ini
(1,5 CPU shared / 8 GB RAM, 6 node berjalan bersamaan selama pengukuran);
tidak ada angka yang dikarang.

## 1. Apa yang dibangun

Fork implementasi terpisah — pohon Jalur A yang jalan
(`build/blackchaind-sdk54-bkc`, `devnet-data-sdk54-bkc`, `testnet-data`)
**TIDAK disentuh**:

| Komponen | Lokasi |
|---|---|
| Salinan scaffold Jalur A | `build/blackchain-phase1/` (salinan `blackchain-sdk54-bkc`) |
| Fork Cosmos EVM v0.7.4 | `build/evm-fork-phase1/` (salinan module cache `evm@v0.7.4`) |
| Binary fork | `build/blackchaind-phase1` (199.315.096 bytes) |
| Devnet fork (1 validator) | `phase1-data/cosmos` (JSON-RPC 127.0.0.1:8755, Comet RPC 26877) |
| Skrip setup devnet fork | `repo/scripts/setup-phase1-devnet.sh` |
| Uji fungsional batch | `repo/scripts/phase1-functional-test.py` |
| Benchmark batch (E2) | `repo/scripts/bench-batch.py` |

Wiring fork: `blackchain-phase1/go.mod` mendapat satu baris tambahan
`replace github.com/cosmos/evm => ../evm-fork-phase1` (pola yang sama
dengan Jalur C Sesi 3). Tidak ada dependensi lain yang diubah.

### 1.1 Endpoint baru: `eth_sendRawTransactionBatch`

`rpc/backend/batch.go` (baru, ~330 baris) + `SendRawTransactionBatch` di
`rpc/backend/backend.go` (interface `EVMBackend`) +
`SendRawTransactionBatch` di `rpc/namespaces/ethereum/eth/api.go`
(interface `EthereumAPI` + `PublicAPI`). Metode diekspos otomatis sebagai
`eth_sendRawTransactionBatch` oleh server JSON-RPC (refleksi nama metode,
sama seperti `eth_sendRawTransaction`).

Semantik (sesuai `docs/16` §3): satu panggilan membawa array maks 100
raw tx (maks 10 MB). Tiap tx diproses independen; hasilnya array dengan
urutan yang sama seperti input: sukses → `{hash}`, gagal →
`{hash: 0x0, error: "..."}`. Satu tx gagal TIDAK menggagalkan batch.

Alur per batch:
- **Fase A — paralel** (worker pool 2×vCPU, maks 32): decode RLP +
  pre-check murah (fee cap > 0, sebelum recover yang mahal) + cek
  replay-protection/chain-id + `FromSignedEthereumTx` (recover pengirim,
  secp256k1 — bagian termahal) + `ValidateBasic` + `BuildTx`.
- **Fase B — sharded submit**: tx dikelompokkan per pengirim, diurutkan
  berdasarkan nonce, lalu tiap kelompok pengirim diserahkan ke salah satu
  dari **16 shard** (fnv hash alamat pengirim). Satu goroutine per shard
  yang tidak kosong; di dalam satu shard, tx dari pengirim yang sama
  diserahkan berurutan (FIFO nonce); pengirim berbeda dalam shard yang
  sama diserahkan berurutan pula, shard berbeda berjalan paralel.
  Penyerahan memakai jalur `Mempool.Insert` yang sama dengan endpoint
  tunggal (tidak ada jalur pintas baru ke txpool).
- Bila satu tx gagal di `Insert`, tx berikutnya dari pengirim yang sama
  di batch itu mendapat error eksplisit `held: preceding transaction
  from 0x... failed` (bukan dibuang diam-diam — client bisa retry).
- Duplikat nonce dari pengirim yang sama di dalam satu batch ditolak
  dengan `duplicate nonce N in batch`.

### 1.2 Proteksi DoS (`docs/16` §2.4)

Diterapkan di `rpc/backend/batch.go` (`batchRateLimiter`, in-memory,
per node):
- maks 100 tx / batch, maks 10 MB / batch (ditolak dengan error jelas);
- maks 4 panggilan batch bersamaan (semaphore);
- 20 tx/detik per pengirim (sliding window 1 detik);
- maks 100 tx tertunda (in-flight insert) per pengirim;
- dedup hash cepat (cache 100.000 hash terakhir, FIFO eviction).
- Floor harga gas jaringan (base fee) **tetap** ditegakkan oleh mempool
  insert seperti pada jalur tunggal (tidak diduplikasi di sini).

### 1.3 Yang SENGAJA tidak diubah: lock internal mempool Krakatoa

Pemeriksaan kode (`mempool/mempool.go`, `mempool/internal/queue/queue.go`,
`mempool/txpool/`): mempool EVM adalah fork go-ethereum TxPool
(`txPool` + `LegacyPool` + satu `evmInsertQueue` FIFO dengan SATU
goroutine konsumen yang memanggil `txPool.Add` secara batch). Rewrite
16-shard atas struktur ini berarti mengubah locking, validasi
(nonce/saldo via StateDB bersama), dan ordering prioritas di dalam
txpool — perubahan ribuan baris dengan risiko regresi tinggi (termasuk
risiko app-hash divergen), dan tidak bisa diuji tuntas dalam satu sesi.

Keputusan Sesi 9: sharding diterapkan di **lapisan admission** (urutan
masuk + paralelisasi recover), bukan di dalam txpool. Pengukuran E2
menunjukkan apakah itu cukup (lihat §5). Rewrite shard txpool internal
didefinisikan sebagai **Fase 1b** (pekerjaan lanjutan, lihat §6).

## 2. Build

Perintah (dari `build/blackchain-phase1/`):
```
export PATH=/home/hatch/go-install/go/bin:$PATH
export TMPDIR=$HOME/workspace/.build-tmp/go-tmp
go vet github.com/cosmos/evm/rpc/backend github.com/cosmos/evm/rpc/namespaces/ethereum/eth
go build -p 2 -o /home/hatch/workspace/blackchain/build/blackchaind-phase1 ./cmd/blackchaind
```
Hasil: `go vet` lolos (0 temuan), `go build` lolos, binary
`build/blackchaind-phase1` 199.315.096 bytes.

### Kegagalan build (F35)

- **F35 — link gagal "no space left on device".** Penyebab: linker
  eksternal (gcc) menulis file sementara ke `/tmp/go-link-*`, dan
  `/tmp` adalah tmpfs 512 MB (kegagalan yang sama dengan F20 Sesi 3).
  Perbaikan: `TMPDIR=$HOME/workspace/.build-tmp/go-tmp` (disk
  /home/hatch, 144 GB bebas). Build kontrol fork yang belum diubah
  sebelumnya gagal di langkah link dengan pesan yang sama; setelah
  TMPDIR diubah, build lolos. Pelajaran: semua build Go di VM ini
  WAJIB memakai TMPDIR di workspace.
  (Catatan penomoran: kegagalan ini terjadi SEBELUM reboot F34, tetapi
  dicatat F35 karena Sesi 12 sudah lebih dulu memakai nomor F34 untuk
  reboot VM di `docs/23` §5 dan `docs/24` §3.5 — nomor tidak boleh
  bentrok antar dokumen.)

## 3. Uji fungsional (fork devnet 1 validator, live)

Node fork dijalankan dari `phase1-data/cosmos` (setup:
`repo/scripts/setup-phase1-devnet.sh`, genesis tervalidasi):
RPC 26877, P2P 26876, JSON-RPC 127.0.0.1:8755, WS 8756.
Perintah start ada di `phase1-data/cosmos-node.log` (header file).

Skrip uji: `repo/scripts/phase1-functional-test.py`
(dijalankan 2×, semua lolos):

| # | Uji | Hasil |
|---|---|---|
| 1 | `eth_chainId` | `0x1352900` (20261120) ✓ |
| 2 | Transfer tunggal `eth_sendRawTransaction` 1.000.000 wei | tx `0x0749622f…` (run 1) / `0xb587c693…` (run 2), receipt status `0x1`, penerima +1.000.000 wei tepat ✓ |
| 3 | Batch 10 transfer (1 pengirim, nonce berurutan) | 10/10 hash dalam 0,01 dtk; semua receipt `0x1`; semua penerima +1.000.000 wei ✓ |
| 4a | Batch 101 tx | ditolak: `batch too large: 101 transactions, max 100` ✓ |
| 4b | Batch campuran (1 tx RLP invalid + 1 tx valid) | tx invalid error `transaction decoding failed: rlp: value size exceeds...`, tx valid sukses (receipt `0x1`) — batch tidak gagal total ✓ |
| 4c | Tx duplikat 2× dalam satu batch | pertama diterima, kedua ditolak `duplicate nonce 23 in batch` ✓ |

Kunci privat validator di-export IN-MEMORY saja selama pengujian
(`keys export --unarmored-hex --unsafe -y` via subprocess); tidak
pernah dicetak atau ditulis ke disk.

## 4. Devnet fork vs pohon Jalur A

Pohon Jalur A tidak disentuh: devnet BKC (PID 2980, JSON-RPC 8555)
dan testnet rehearsal 4 validator (PID 12799–12976) tetap berjalan
selama Sesi 9. Node fork berjalan terpisah (port 8755/26877) dan
tidak terhubung (peer) ke jaringan lain.

## 5. Pengukuran E1/E2 (di VM 1,5 CPU — label wajib)

SEMUA hasil di bawah ini terukur di VM yang sama (1,5 CPU shared,
8 GB RAM) dengan 6 node berjalan bersamaan (devnet BKC + testnet
4 validator + devnet fork). Angka ini adalah perbandingan RELATIF
antar konfigurasi di VM yang sama, BUKAN klaim absolut.

### 5.1 E1 — baseline fork, endpoint tunggal (`bench-evm.py`)

Prosedur Sesi 4 (blok ~5 detik, 20 akun × 50 transfer = 1.000 tx;
contract 500× `increment()`), 3 run tiap mode, 0 tx gagal di semua run:

| Run | Transfers sustained | Transfers submitted | Transfers p50 | Contract sustained | Contract submitted | Contract p50 |
|---|---|---|---|---|---|---|
| 1 | 59,82 TPS | 90,93 tx/dtk | 8,81 dtk | 51,09 TPS | 111,04 tx/dtk | 5,30 dtk |
| 2 | 60,66 TPS | 98,08 tx/detik | 8,83 dtk | 47,92 TPS | 105,85 tx/detik | 4,18 dtk |
| 3 | 63,04 TPS | 96,77 tx/detik | 7,85 dtk | 49,20 TPS | 115,05 tx/detik | 5,14 dtk |
| **Rata-rata** | **~61,2 TPS** | **~95,3 tx/detik** | **~8,5 dtk** | **~49,4 TPS** | **~110,6 tx/detik** | **~4,9 dtk** |

Perbandingan vs Sesi 4 iterasi 1 (blok 5 dtk, Jalur A): 66,29 TPS
transfers / 57,15 TPS contract, submit ~100–118 tx/detik. Fork TIDAK
regresif secara material (selisih dalam noise + CPU VM kini dibagi
6 node, bukan 1–2 node seperti Sesi 4). Detail per run:
`~/workspace/.build-tmp/phase1-bench/e1-*.json`.

### 5.2 E2 — batch endpoint (`bench-batch.py`)

Prosedur: tx pre-signed (signing di luar jendela ukur), di-submit dalam
batch maks 100 tx, jeda antar batch 0,5 dtk (agar laju per pengirim
tetap di bawah limiter 20 tx/dtk — lihat catatan di bawah). Transfers:
1.000 tx (20 akun × 50, interleaved). Contract: 500× `increment()`
(20 akun × 25, interleaved, deploy baru tiap run).

| Run | Transfers submit | Transfers sustained | Transfers p50 | Contract submit | Contract sustained | Contract p50 |
|---|---|---|---|---|---|---|
| 1 | 202,31 tx/dtk (4,94 dtk) | 85,72 TPS | 4,10 dtk | 230,46 tx/dtk (2,17 dtk) | 4,79 TPS * | 7,58 dtk |
| 2 | 201,09 tx/dtk (4,97 dtk) | 91,98 TPS | 3,03 dtk | 233,30 tx/dtk (2,14 dtk) | 4,94 TPS * | 4,22 dtk |
| 3 | 209,40 tx/dtk (4,78 dtk) | 84,22 TPS | 4,22 dtk | 227,65 tx/dtk (2,20 dtk) | 49,56 TPS | 0,98 dtk |
| 4 | — | — | — | 234,18 tx/dtk (2,14 dtk) | 49,07 TPS | 7,28 dtk |
| 5 | — | — | — | 121,37 tx/dtk (4,12 dtk, jeda 1,0 dtk) | 39,24 TPS ** | 1,69 dtk |
| **Rata-rata bersih** | **~204 tx/dtk** | **~87,3 TPS** | **~3,8 dtk** | **~231 tx/dtk** (run 3–4) | **~49,3 TPS** (run 3–4) | — |

\* Run contract 1–2: 476/500 sukses; 24 tx per run DITOLAK saat submit
(alasan tidak terekam — bug harness F39, lihat §5.4). Angka sustained
4,79/4,94 TPS di run itu adalah artefak fase receipt yang menunggu
tx yang tidak pernah ada, BUKAN kapasitas chain.
\** Run 5 memakai jeda batch 1,0 dtk (uji hipotesis limiter): submit
lebih lambat sehingga window lebih panjang dan sustained tampak lebih
rendah — artefak prosedur, bukan kapasitas chain.

**Probe laju submit mentah** (1 batch × 100 tx, tanpa jeda):
**1.300,95 tx/detik dalam 0,077 dtk** (100/100 sukses). Ini plafon
mentah endpoint di VM ini — bukan angka sustained.

### 5.3 Kesimpulan pengukuran

Perbandingan E1 → E2 (rata-rata, VM yang sama, 6 node berjalan):

| Metrik | E1 (endpoint tunggal) | E2 (batch) | Perubahan |
|---|---|---|---|
| Transfers sustained | 61,2 TPS | 87,3 TPS | **+43%** |
| Transfers submit rate | 95,3 tx/dtk | ~204 tx/dtk (dibatasi jeda 0,5 dtk); 1.301 tx/dtk mentah | **+114% / ~13,7× mentah** |
| Transfers latensi p50 | ~8,5 dtk | ~3,8 dtk | **−55%** |
| Contract sustained | 49,4 TPS | ~49,3 TPS (run bersih 3–4) | **tidak berubah** |
| Contract submit rate | 110,6 tx/dtk | ~231 tx/dtk (dibatasi jeda) | **+109%** |

**Fase 1 BERHASIL menghilangkan bottleneck ingest.** Submit rate naik
lebih dari 10× (mentah) dan latensi p50 transfer turun lebih dari
separuh. Kenaikan sustained transfer (+43%) berhenti di bottleneck
BERIKUTNYA: produksi blok (~5 dtk/blok, ~430–500 transfer/blok
teramati di E2 — tiap run 1.000 tx masuk dalam ~2 blok). Untuk
contract, sustained TIDAK naik sama sekali: 500 panggilan butuh
~2 blok × ~250 panggilan (gas per panggilan 62.220, eksekusi EVM
serial) — bottleneck-nya kapasitas blok + eksekusi serial, bukan
ingest. Inilah yang diramalkan docs/10: ingest paralel menaikkan
plafon tahap 1 (300–1.000 TPS) hanya bila blok + eksekusi ikut
dinaikkan; di VM 1,5 CPU ini plafon terukur tahap 1 adalah ~87 TPS
transfer / ~49 TPS contract. **100.000 TPS tetap TARGET, jarak
~1.100× — tidak ada klaim baru di sini.**

Catatan batas ukur: (a) angka submit E2 dibatasi jeda antar batch
(0,5 dtk) yang sengaja dipasang agar tidak menabrak limiter
20 tx/dtk/pengirim — angka "mentah" 1.301 tx/dtk hanya dari probe
100 tx; (b) 6 node berbagi 1,5 CPU selama pengukuran; (c) dua reboot
VM (F35) memotong run E2 yang gagal — angka di atas berasal dari
run yang selesai penuh setelah reboot terakhir.

### 5.4 Kegagalan yang ditemukan saat pengukuran (F34, F36–F40)

- **F34 — VM reboot 3× (±17:27, ±18:41, dan ±18:46 UTC, 20 Nov 2026;
  21 Nov 00:27, 01:41, 01:46 WIB).**
  `uptime` menunjukkan "up 0–1 min" setelah tiap kejadian; semua node
  (devnet BKC, 4 validator testnet, devnet fork) + proses benchmark
  mati bersamaan; log tiap node berakhir dengan penutupan graceful
  (SIGTERM saat shutdown). Bukan `pkill` dan bukan ulah agen (tidak
  ada yang menjalankan pkill di sesi ini). Data di disk selamat;
  semua node dinyalakan ulang dari home masing-masing.
  Kejadian pertama didokumentasikan Sesi 12 sebagai F34
  (`docs/23` §5, `docs/24` §3.5) beserta runbook pemulihan;
  Sesi 12 membuat `scripts/restart-local-nodes.sh` (di root blackchain,
  di luar repo — sengaja TIDAK menyentuh node fork Sesi 9) dan Sesi 13
  memperluas `repo/scripts/restart-all-nodes.sh` (skrip Sesi 9 ini)
  agar juga menyalakan faucet + BlackScan. Pemulihan pasca-reboot
  memakai kedua skrip itu dan terbukti: BKC height 17069, val 1649
  sinkron, fork 1461. Run E2 yang sedang berjalan ikut terbunuh di
  reboot pertama dan kedua; angka §5.2–5.3 berasal dari run penuh
  setelah reboot terakhir.
- **F36 — pre-check fee cap batch terlalu ketat (bug implementasi).**
  Versi pertama `prepareBatchTx` menolak fee cap 0 (`Sign() <= 0`),
  padahal di chain ini (base fee 0 saat blok kosong, minimum-gas-prices
  0) tx gasPrice 0 VALID dan diterima jalur tunggal. Akibat: batch
  ditolak 100% saat `eth_gasPrice` sempat 0. Perbaikan: tolak hanya
  fee cap negatif; floor base fee tetap ditegakkan mempool insert.
  Diverifikasi: batch 3 tx gasPrice 0 → 3 hash.
- **F37 — `wait_receipt` di `bench-batch.py` salah membaca envelope
  RPC.** `Rpc.call` mengembalikan `result` langsung, tapi
  `wait_receipt` memanggil `.get("result")` pada `None` → AttributeError
  pada poll pertama saat receipt belum ada. Run E2 pertama (3 run)
  mati karenanya. Perbaikan: cek `rec` langsung.
- **F38 — restart node fork membunuh PID yang salah.** `pgrep -f
  "blackchaind-phase1 start"` mengembalikan PID shell pembungkus
  (cmdline-nya mengandung pola), bukan node; `kill` mematikan shell,
  node lama (PID 16598, binary lama) tetap jalan dan start baru gagal
  bind port — probe masih menunjukkan error lama. Perbaikan: kill PID
  node persis dari `ps` (cmdline diawali `./build/blackchaind-phase1
  start`), verifikasi port mati, baru start ulang. Pelajaran: JANGAN
  `pgrep -f` dengan pola yang juga cocok dengan shell pemanggil.
- **F39 — harness `bench-batch.py` menghitung hash nol sebagai sukses.**
  Tx yang ditolak batch kembali sebagai `{hash: 0x0000…0000, error}`.
  `submit_batches` memeriksa `if r.get("hash")` — string hash nol
  tidak kosong sehingga lolos sebagai "submitted", lalu fase receipt
  mem-poll hash nol sampai timeout (45 dtk × 24 tx). Akibat: run
  contract-batch 1–2 tercatat 476/500 dengan 24 "receipt timeout"
  dan sustained semu ~4,8 TPS; alasan penolakan 24 tx itu HILANG
  (tidak terekam). Perbaikan: hash nol = gagal, error-nya dicatat;
  fase receipt memakai `as_completed` (bukan `map` berurutan) agar
  satu tx lambat tidak memblokir seluruh fase. Hipotesis utama
  penolakan 24 tx: limiter 20 tx/dtk/pengirim di ambang batas (5 batch
  × 5 tx/pengirim dalam 2,1 dtk — bursty dalam window 1 dtk) — BELUM
  terbukti; run 3–5 bersih dengan prosedur sama. Uji ulang dengan jeda
  1,0 dtk sudah dilakukan (run 5): bersih 500/500. Tindak lanjut yang
  tersisa: retry otomatis untuk tx yang ditolak limiter (belum dibuat).
- **F40 — `bench-batch.py` contract-batch awal: 5 akun × 100 call.**
  Tiap batch 100 tx berisi 20 tx dari satu pengirim → limiter 20/dtk
  menolak batch 2–5; hanya ~258/500 call yang masuk (terbukti lewat
  nilai counter 258 dan nonce akun). Bukan bug chain — prosedur bench
  yang salah. Perbaikan: 20 akun × 25 call (5/pengirim/batch), sama
  seperti transfers. Pelajaran: desain beban HARUS menghormati
  limiter yang diuji, kalau tidak yang terukur adalah limiternya.

## 6. Yang belum dikerjakan / langkah berikut

- **Fase 1b — shard txpool internal:** paralelisasi validasi di
  `txPool.Add` (per-tx StateDB snapshot) + evaluasi apakah insert
  queue tunggal masih menjadi funnel setelah E2. Butuh kajian
  determinisme (app-hash harus identik) + uji regresi berat sebelum
  dipakai di testnet.
- **E1 di hardware layak** (blokir B — belum ada anggaran): baseline
  di server 16 vCPU/64 GB/NVMe; angka absolut hanya bermakna di sana.
- **Node RPC khusus** (`docs/16` §4): 2–4 node RPC di depan validator
  belum dibangun (butuh server).
- **Uji DoS batch** di devnet sebelum testnet (rate limit 20 tx/dtk
  per pengirim + batas batch) — skrip uji belum ditulis.
- **Rebase ke Cosmos EVM baru** bila ada rilis (watch 27 Nov 2026):
  diff fork ini kecil (3 file + 1 file baru di `rpc/`), direkam di §7.

## 7. Diff fork (ringkas)

File yang diubah di `build/evm-fork-phase1/` (relatif terhadap
`evm@v0.7.4` dari module cache):
- `rpc/backend/batch.go` — BARU: `SendRawTransactionBatch`, worker
  pool Fase A, sharded submit Fase B, `batchRateLimiter`.
- `rpc/backend/backend.go` — `Backend.batchLimiter` (field + init di
  `NewBackend`); `SendRawTransactionBatch` di interface `EVMBackend`.
- `rpc/namespaces/ethereum/eth/api.go` — `SendRawTransactionBatch`
  di interface `EthereumAPI` + metode `PublicAPI`.
- `build/blackchain-phase1/go.mod` — 1 baris: `replace
  github.com/cosmos/evm => ../evm-fork-phase1`.
- `repo/scripts/setup-phase1-devnet.sh`, `repo/scripts/phase1-functional-test.py`,
  `repo/scripts/bench-batch.py` — BARU (tooling sesi ini).

Tidak ada perubahan pada `x/vm`, `mempool`, `ante`, `x/feemarket`,
atau genesis/parameter chain. Eksekusi tetap serial; app-hash tidak
terpengaruh oleh perubahan admission (urutan masuk mempool per
pengirim tetap FIFO nonce; urutan eksekusi ditentukan konsensus
seperti sebelumnya).
