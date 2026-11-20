# BLACKCHAIN — Laporan Benchmark TPS EVM (Sesi 4, 2026-11-20)

Laporan ini mencatat SEMUA pengukuran TPS yang benar-benar dijalankan di devnet
lokal BLACKCHAIN. Tidak ada angka yang dikarang. Teoretis / lab / sustained /
finalized dipisah dengan jelas.

## 0. Lingkungan pengukuran (dicatat, bisa diulang)

- **Chain yang diukur:** devnet identitas BKC `blackchain_20261120-1`,
  EVM chain ID **20261120** (`0x1352900`), denom `abkc` (1 BKC = 10^18 abkc),
  binary `build/blackchaind-sdk54-bkc` (Cosmos SDK v0.54.5 + Cosmos EVM v0.7.4).
- **Node:** 1 validator lokal, mempool Krakatoa (`mempool.type = "app"`),
  EVM JSON-RPC `127.0.0.1:8555`, CometBFT RPC `127.0.0.1:26677`.
- **Harness:** `scripts/bench-evm.py` (stdlib + eth_account 0.14.0; lihat
  `docs/08-benchmark-harness.md`). Mode `transfers` = self-transfer 1 wei
  per tx (21.000 gas); mode `contract` = deploy SimpleCounter lalu N kali
  `increment()` (SSTORE, ~50k gas per call).
- **Perangkat keras:** VM Linux, CPU AMD EPYC 9D25 (nproc 4, cell runtime
  dibatasi ~1,5 CPU shared), RAM 8 GB (7934 MB), disk 150 GB (145 GB free),
  load average saat pengukuran ~0,7–1,0. Node + harness berjalan di VM yang
  sama (bersaing CPU).
- **Definisi TPS di sini:** *sustained TPS* = jumlah tx sukses / durasi total
  jendela (submit pertama → receipt terakhir). *Finalized TPS* = tx yang
  masuk blok yang sudah difinalisasi CometBFT (semua tx di laporan ini
  difinalisasi — receipt hanya keluar setelah blok commit; jadi sustained =
  finalized di devnet 1 validator ini). *Submitted TPS* = laju pengiriman
  mentah harness (bukan throughput chain).
- **Biaya gas selama pengukuran:** feemarket EIP-1559 aktif; gasPrice
  meluruh dari ~753 jt wei → ~0 wei karena blok-blok kosong (base fee
  turun). Semua tx dalam laporan ini praktis gratis; biaya bukan faktor
  pembatas.

## 1. Hasil per iterasi

| Iterasi | Konfigurasi blok | Beban | Sukses | TPS sustained (finalized) | TPS submitted | Latensi p50 | Latensi p95 | tx/blok maks |
|---|---|---|---|---|---|---|---|---|
| 0 (Jalur A lama, chain 262144) | 5,0 dtk | contract 20 calls | 20/20 | **3,05** | 123,0 | 6,45 dtk | 6,50 dtk | 20 |
| 1 | 5,0 dtk (timeout_commit 5s) | transfers 10×100 = 1000 | 1000/1000 | **66,29** | 112,1 | 8,11 dtk | 8,76 dtk | 518 |
| 1 | 5,0 dtk | contract 500 calls | 500/500 | **57,15** | 124,2 | 5,08 dtk | 5,52 dtk | 500 |
| 2 | 1,0 dtk (timeout_commit 1s) | transfers 10×100 = 1000 | 1000/1000 | **82,08** | 106,5 | 6,23 dtk | 9,11 dtk | 138 |
| 2 | 1,0 dtk | contract 500 calls | 500/500 | **80,91** | 108,7 | 3,14 dtk | 4,46 dtk | 140 |
| 2b | 1,0 dtk | transfers 20×50 = 1000 | 1000/1000 | **73,19** | 100,8 | 7,15 dtk | 9,95 dtk | 155 |
| 3 | 0,5 dtk (timeout_commit 500ms) | transfers 10×100 = 1000 | 1000/1000 | **87,31** | 109,3 | 5,78 dtk | 8,92 dtk | 87 |
| 3 | 0,5 dtk | contract 500 calls | 500/500 | **89,24** | 116,4 | 2,69 dtk | 4,12 dtk | 89 |
| 4 | 0,5 dtk SEMUA timeout (propose/prevote/precommit/commit 500ms) | transfers 10×100 = 1000 | 1000/1000 | **87,50** | 110,8 | 5,87 dtk | 8,90 dtk | 89 |
| 4 | 0,5 dtk SEMUA timeout | contract 500 calls | 500/500 | **88,68** | 117,8 | 2,82 dtk | 4,11 dtk | 84 |

Hasil mentah (JSON): `~/workspace/.build-tmp/bench-bkc-*.json`
(perintah lengkap tiap run ada di `docs/08-benchmark-harness.md` §7.3).

**Angka maksimum terukur yang jujur: ~89 TPS sustained (finalized)**
— contract 500 calls, iterasi 3: **89,24 TPS**; transfers 1000 tx,
iterasi 4: **87,50 TPS**. Semua run 0 gagal (0 tx gagal submit, 0 receipt
timeout). Counter akhir `counter()` = 500 pada setiap run contract
(cocok dengan jumlah increment sukses).

## 2. Apa yang berubah antar iterasi (dan efeknya)

- **Iterasi 1 → 2 (block time 5 dtk → 1 dtk):** +24% transfers, +42%
  contract. Block time adalah bottleneck utama pada iterasi 1: dengan
  5 dtk/blok, sustained TPS ≈ tx-per-blok / 5 dtk.
- **Iterasi 2 → 3 (1 dtk → 0,5 dtk):** +6% transfers, +10% contract.
  Keuntungan mengecil: block time di bawah beban tetap ~1,0 dtk
  (biaya tetap per blok: propose → prevote → precommit → commit +
  eksekusi + tulis disk tidak bisa ditekan hanya dengan timeout).
- **Iterasi 3 → 4 (semua timeout 500ms):** ±0% (87,31→87,50 transfers;
  89,24→88,68 contract). **Plateau terkonfirmasi** — tuning timeout
  CometBFT sudah habis.
- **Iterasi 2b (20 akun × 50, paralelisme ganda):** TPS MALAH TURUN
  (82,08 → 73,19). Menambah thread pengirim tidak menaikkan throughput:
  submit rate mentok di ~100–118 tx/detik di semua run.

## 3. Diagnosis bottleneck (berdasarkan data, bukan dugaan)

1. **Ingest JSON-RPC + mempool (~100–118 tx/detik) — bottleneck utama.**
   Laju submit harness tidak pernah melewati ~118 tx/detik meski thread
   digandakan (10 → 20 akun). Setiap `eth_sendRawTransaction` harus
   melewati: unmarshal RLP → recover pengirim (secp256k1) → cek
   nonce/saldo via StateDB → insert ke mempool Krakatoa (dengan lock).
   Pada VM 1,5 CPU shared, jalur ini efektif serial. Bukti: tx per blok
   ≈ laju ingest × block time di semua iterasi (5 dtk→~500/blok,
   1 dtk→~130/blok, 0,5 dtk→~85/blok).
2. **Biaya tetap per blok CometBFT (~1,0 dtk di bawah beban).** Walau
   timeout_commit 500ms, block time rata-rata saat beban tetap 1,0 dtk
   (blok kosong: ~0,67 dtk). Satu putaran konsensus BFT penuh
   (propose/prevote/precommit/commit) + eksekusi + commit state tidak
   bisa di bawah itu di stack ini tanpa mengubah arsitektur.
3. **Eksekusi EVM serial.** Cosmos EVM mengeksekusi tx satu per satu
   dalam satu blok (tidak ada eksekusi paralel di v0.7.4). Pada beban
   contract (SSTORE berurutan ke slot yang sama) ini menambah antrean,
   tapi bukan pembatas utama — transfer sederhana (21k gas) pun mentok
   di angka yang sama.
4. **Bukan gas limit blok.** `eth_getBlockByNumber` menunjukkan
   `gasLimit = 4.294.967.295` (0xffffffff); 500 transfer hanya memakai
   ~10,5 jt gas. Bukan mempool size (tidak ada tx yang ditolak).
   Bukan kegagalan jaringan (localhost, 1 validator).

## 4. Target 100.000 TPS — penilaian jujur

**Tidak tercapai di devnet lokal ini, dan bukan karena kurang mencoba.**
Jaraknya ~1.100× dari maksimum terukur (~89 TPS). Ini BUKAN kegagalan
pengukuran — ini hasil yang valid dan penting: arsitektur saat ini
(Cosmos SDK + CometBFT + Cosmos EVM v0.7.4, eksekusi serial, 1 validator,
VM kecil) secara struktural berada di orde ~10² TPS, bukan ~10⁵ TPS.

Yang harus berubah untuk mendekati 100.000 TPS (urutan prioritas):

1. **Eksekusi paralel / Block-STM** — eksekusi tx paralel dengan
   deteksi konflik (seperti Aptos/Sui/Sei). Tanpa ini, satu core CPU
   adalah langit-langit. Ini perubahan arsitektur terbesar; Cosmos EVM
   v0.7.4 tidak menyediakannya.
2. **Mempool + ingest paralel** — admission tx paralel, batching,
   dan/atau beberapa node JSON-RPC di depan satu validator (atau
   sharding mempool). Ingest ~110 tx/detik harus naik ~1.000×.
3. **Konsensus lebih cepat / block time sub-detik nyata** — CometBFT
   dengan 1 validator masih ~1 dtk/blok di bawah beban; butuh
   optimasi (mis. Skip timeout, async commit) atau konsensus lain
   (mis. Narwhal/Tusk, HotStuff) — semuanya riset/engineering besar.
4. **Hardware kelas server** — CPU multi-core cepat (bukan 1,5 CPU
   shared), NVMe, RAM besar; lalu ukur lagi. Hardware saja tidak cukup
   (lihat poin 1–3), tapi tanpa hardware yang layak pengukuran tidak
   bermakna.
5. **Sharding / app-chain paralel** — bila satu chain tetap mentok,
   throughput agregat bisa naik lewat beberapa chain paralel + bridge
   (tapi itu bukan 100.000 TPS *per chain*).
6. **Benchmark dengan beban realistis multi-node** — ukur ulang di
   testnet multi-validator dengan beban ribuan tx/detik sebelum
   mengklaim angka apa pun.

**Kesimpulan untuk pemilik:** klaim 100.000 TPS tetap berstatus
**TARGET JANGKA PANJANG, BUKAN HASIL TERUKUR**. Angka yang boleh
diklaim hari ini: **~89 TPS sustained (finalized) di devnet lokal
1 validator** (transfer & contract call sederhana). Angka teoretis
kasar dari batas yang terlihat (gasLimit/blok ÷ gas/tx ÷ block time)
tidak dilaporkan sebagai hasil, karena tidak pernah tercapai dalam
pengukuran — melaporkan angka itu akan menyesatkan.

## 5. Finality & latensi

- Finality: instan setelah commit blok (BFT, >2/3 voting power; 1
  validator = final begitu blok di-commit). Semua receipt di laporan
  ini adalah tx yang sudah final.
- Latensi submit→receipt: p50 2,7–8,1 dtk tergantung beban & block
  time; p95 4,1–9,9 dtk. Latensi didominasi antrean mempool +
  block time, bukan eksekusi (satu transfer dieksekusi dalam
  milidetik).
