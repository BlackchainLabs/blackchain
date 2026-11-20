# BLACKCHAIN — Desain Implementasi Fase 1: Ingest Paralel (Sesi 7, 2026-11-20)

**Status:** DESAIN IMPLEMENTASI — dokumen ini merinci APA yang dibangun
dan BAGAIMANA diukur. Tidak ada kode chain yang ditulis di sesi ini;
implementasi adalah sesi berikutnya. Semua angka plafon adalah ESTIMASI
dari `docs/10` §6, bukan hasil ukur.

**Keputusan pemilik Sesi 7 (disampaikan lewat Muse utama):** urutan
Fase 1→4 dari `docs/10` §7 **DISETUJUI**. Fase 1 = hardware layak +
ingest paralel + batch RPC. Konsekuensi yang diterima: implementasi
Fase 1–2 berarti **memelihara fork Cosmos EVM v0.7.4** (biaya
maintenance jangka panjang: tiap rilis upstream harus di-rebase,
pelajaran dari Jalur C Sesi 3) — atau menunggu upstream menyediakan
eksekusi paralel, yang belum ada sampai 20 Nov 2026.

**Titik awal terukur (Sesi 4, `docs/09`):** ingest JSON-RPC + mempool
Krakatoa mentok **~100–118 tx/detik**; TPS sistem maks ~89 TPS.
Bottleneck #1 yang terbukti adalah ingest, bukan gas limit.

## 1. Arsitektur saat ini (yang diubah)

Jalur satu transaksi masuk hari ini (satu koneksi, serial):

```
eth_sendRawTransaction
  → unmarshal RLP
  → recover pengirim (secp256k1 — mahal, ~50–100 µs/tx/core)
  → cek nonce + saldo via StateDB
  → insert ke mempool Krakatoa (lock)
  → gossip ke peer (BroadcastTx)
```

Semua langkah di atas terjadi berurutan per koneksi. Menambah thread
di level HTTP tidak membantu karena recover + cek state + insert
mempool tetap serial dan saling mengunci.

## 2. Desain worker pool CheckTx paralel

### 2.1 Prinsip

Pisahkan pekerjaan menjadi dua tahap dengan batas yang jelas:

- **Tahap A — admission paralel (tanpa lock global):** recover
  signature, validasi format, cek gas minimum, cek saldo + nonce
  terhadap snapshot state yang dibaca secara read-only. Dijalankan
  paralel oleh worker pool.
- **Tahap B — insert mempool (serial singkat):** hanya operasi yang
  benar-benar butuh lock — memasukkan tx ke mempool dalam urutan nonce
  yang benar. Lock dipegang sesingkat mungkin (tidak ada I/O dan
  tidak ada recover di dalam lock).

### 2.2 Parameter desain

| Parameter | Nilai desain | Alasan |
|---|---|---|
| Jumlah worker admission | **2 × jumlah vCPU** (contoh: 32 worker di server 16 vCPU) | Recover secp256k1 adalah CPU-bound; 2× vCPU memberi ruang saat sebagian worker menunggu I/O StateDB. Nilai awal — diukur ulang di E2 |
| Antrean per pengirim (FIFO) | Satu antrean FIFO per alamat pengirim; worker mengambil tx dari antrean yang berbeda secara paralel, tapi tx dari pengirim yang sama diproses berurutan | Nonce harus masuk mempool dalam urutan naik; tx nonce 5 tidak boleh mendahului nonce 4 dari pengirim yang sama |
| Timeout admission | **2 detik** per tx; tx yang melewati batas ditolak dengan error jelas (client retry) | Mencegah antrean menumpuk tanpa batas saat beban melonjak |
| Ukuran antrean global | **10.000 tx** menunggu admission; di atas itu RPC menolak dengan `429 / mempool full` | Backpressure eksplisit lebih baik daripada latensi yang membengkak diam-diam |
| Lock mempool | Lock per-shard, bukan satu lock global: mempool di-shard berdasarkan **hash alamat pengirim** (16 shard) | Insert dari pengirim berbeda tidak saling memblokir; insert dari pengirim yang sama tetap berurutan karena satu shard + FIFO |
| Batas mempool per akun | **Maks 100 tx tertunda per pengirim** | Mencegah satu pengirim membanjiri mempool |
| Validasi ulang saat insert | Cek nonce + saldo diulang di dalam lock (murah, read dari cache) | State bisa berubah antara Tahap A dan Tahap B (tx lain dari pengirim yang sama masuk duluan); validasi ulang mencegah tx basi masuk mempool |

### 2.3 Urutan nonce — aturan yang tidak boleh dilanggar

1. Tx dari satu pengirim diproses dalam urutan nonce naik (FIFO).
2. Bila tx nonce N gagal validasi, tx nonce N+1, N+2, … dari pengirim
   yang sama **ditahan** (bukan dibuang) sampai N berhasil atau sampai
   timeout antrean; penolakan out-of-order harus memberi tahu client
   nonce yang diharapkan.
3. Duplikat (hash tx sama) ditolak di Tahap A lewat cache hash
   berukuran terbatas (mis. 100.000 hash terakhir).

### 2.4 Proteksi DoS (wajib — ingest paralel memperlebar permukaan serangan)

| Proteksi | Nilai desain |
|---|---|
| Rate limit per IP | 100 request/detik (tunable); di atas itu 429 |
| Rate limit per pengirim | 20 tx/detik per alamat |
| Gas minimum | Tx di bawah gas price minimum jaringan ditolak di Tahap A (sebelum recover mahal) |
| Ukuran batch | Maks 100 tx per panggilan batch (lihat §3) |
| Biaya admission | Tidak ada biaya tambahan di luar gas; proteksi mengandalkan rate limit + gas minimum |

## 3. Batch endpoint `eth_sendRawTransaction`

- **Endpoint baru:** `eth_sendRawTransactionBatch` (satu HTTP call,
  array berisi maks 100 raw tx) — mengurangi overhead HTTP/TLS per tx.
  Endpoint lama `eth_sendRawTransaction` tetap ada dan tetap bekerja
  (kompatibilitas client).
- **Semantik:** tiap tx dalam batch diproses independen (hasil per tx
  dikembalikan sebagai array: sukses → tx hash; gagal → error per tx).
  Satu tx gagal TIDAK menggagalkan batch.
- **Urutan dalam batch:** tx dari pengirim yang sama dalam satu batch
  diurutkan berdasarkan nonce sebelum masuk antrean FIFO (§2.3).
- **Batas ukuran request:** maks 10 MB per panggilan batch.

## 4. Node RPC khusus di depan validator

Satu validator tidak perlu melayani semua RPC. Arsitektur target Fase 1:

```
Client / load balancer
  → 2–4 node JSON-RPC khusus (non-validator)
      → admission paralel (§2) + batch (§3)
      → forward ke validator via mempool gossip / BroadcastTx
  → validator (hanya propose + eksekusi + konsensus)
```

| Peran | Spesifikasi (ESTIMASI, dari `docs/10` §4) | Tugas |
|---|---|---|
| Validator testnet | 16 vCPU / 64 GB RAM / 2 TB NVMe (≥10k IOPS) / 1 Gbps | Konsensus + eksekusi; TIDAK melayani RPC publik langsung |
| Node RPC (2–4 unit) | 8–16 vCPU / 32–64 GB RAM / 500 GB NVMe | Admission paralel + batch + forward |
| Load balancer | 2 vCPU / 4 GB | Round-robin + health check ke node RPC |

Node RPC tidak menyimpan state konsensus penuh yang harus di-vote;
mereka adalah node penuh (full node) yang mengikuti chain dan
meneruskan tx yang lolos admission. Bila satu node RPC mati, load
balancer memindahkannya — validator tidak terganggu.

## 5. Rencana pengukuran

Tidak ada benchmark baru di Sesi 7 — pengukuran di bawah ini adalah
rencana untuk sesi implementasi. Kriteria lolos diambil dari
`docs/10` §8.

### 5.1 E1 — Baseline di hardware layak

| Item | Isi |
|---|---|
| Tujuan | Mengukur baseline yang bermakna sebelum mengubah kode ingest |
| Perangkat | Server validator 16 vCPU / 64 GB RAM / NVMe (atau setara); 1 validator; `bench-evm.py` (transfers + contract call) |
| Prosedur | 3 run tiap mode (transfer 1.000 tx, contract 500 call), sama seperti `docs/09` |
| Hasil yang dicatat | TPS sustained + latensi p50/p95, ke `docs/09` lanjutan |
| Kriteria lolos | Angka tercatat lengkap dan bisa direproduksi (3 run konsisten); tidak ada target TPS di E1 — E1 hanya baseline |

### 5.2 E2 — Ingest paralel

| Item | Isi |
|---|---|
| Tujuan | Membuktikan laju submit mentah naik sebelum throughput chain diukur |
| Prosedur | (1) Ukur laju submit mentah (tx/detik) ke node RPC dengan worker pool + batch, SEBELUM mengukur TPS chain. (2) Ulangi `bench-evm.py` end-to-end dan bandingkan dengan E1 |
| Hasil yang dicatat | Laju submit mentah, TPS sustained end-to-end, latensi p50/p95, jumlah error per jenis |
| Kriteria lolos | Laju submit **≥ 1.000 tx/detik** tanpa kenaikan error; TPS end-to-end naik vs E1; 0 tx gagal |
| Bila gagal | Turunkan worker ke 1× vCPU, naikkan shard mempool ke 32, atau naikkan batas antrean — satu variabel per percobaan, catat tiap perubahan |

### 5.3 Yang TIDAK diukur di Fase 1

Eksekusi paralel (E3–E5) dan konsensus sub-detik (E6) adalah Fase 2–3.
Fase 1 selesai bila E2 lolos — plafon sistem setelah Fase 1 adalah
**ESTIMASI 300–1.000 TPS** (`docs/10` §6), dan angka pastinya hanya
diketahui setelah E1+E2 dijalankan.

## 6. Risiko implementasi

| Risiko | Mitigasi |
|---|---|
| Nondeterminisme dari paralelisme | Admission paralel TIDAK mengubah urutan eksekusi (eksekusi tetap serial di Fase 1); hanya urutan masuk mempool yang dijaga per pengirim. App-hash tidak terpengaruh |
| Urutan nonce rusak → tx tertahan massal | FIFO per pengirim + validasi ulang di lock (§2.2–2.3); uji beban dengan 20 akun × 50 tx seperti `docs/09` iterasi 2b |
| DoS lewat batch besar | Batas 100 tx/batch + rate limit (§2.4); uji serang di devnet sebelum testnet |
| Fork Cosmos EVM sulit di-rebase | Fork dibuat sebagai patch minimal di atas v0.7.4 dengan diff yang didokumentasikan (pola Jalur C Sesi 3); tiap perubahan dicatat agar rebase ke rilis berikutnya bisa dilakukan |
| Node RPC menjadi titik pusat | 2–4 node + load balancer; validator tetap bisa menerima tx langsung bila semua node RPC mati (jalur darurat) |

## 7. Lingkup sesi berikutnya (implementasi)

1. Fork Cosmos EVM v0.7.4 di direktori terpisah (pohon Jalur A tidak
   diubah sampai terbukti).
2. Implementasi worker pool + shard mempool + batch endpoint.
3. E1 di hardware baru, lalu E2; hasil ditulis ke `docs/09` lanjutan.
4. Bila E2 lolos: lanjut desain Fase 2 (eksekusi paralel, E3).
