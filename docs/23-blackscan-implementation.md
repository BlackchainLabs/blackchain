# BLACKCHAIN — Implementasi BlackScan Lite v0.1 (Sesi 12, 2026-11-20)

**Status:** IMPLEMENTASI JALAN (bukan spek lagi). Spek awal: `docs/11-blackscan-spec.md`.
Kode: `repo/blackscan/` (`blackscan.py`, `start.sh`, `README.md`).
Server live: `127.0.0.1:8081` (lokal saja).

## 1. Keputusan: BUKAN Blockscout (jujur)

Blockscout penuh butuh Elixir/Phoenix + PostgreSQL 17 + archive node
(`pruning = "nothing"`, tracing aktif) + Redis opsional — tidak masuk akal
di VM ini (1,5 CPU berbagi, 8 GB RAM) untuk rantai rehearsal ~900 blok
dengan 2 transaksi. Yang dibangun: **BlackScan Lite** — indexer Python
stdlib + SQLite (WAL) + `http.server`, satu file `blackscan.py` (~450 baris),
tanpa dependensi.

Konsekuensi yang dicatat jujur:
- TIDAK ada verifikasi kontrak, token ERC-20/holder, internal tx/trace,
  halaman validator, grafik, atau kompatibilitas API Etherscan
  (semua itu ada di `docs/11` §3/§5 sebagai target Blockscout penuh).
- Indexer membaca dari node validator val1 (bukan archive node khusus) —
  dapat diterima untuk rehearsal; untuk testnet publik butuh node RPC
  khusus sesuai `docs/11` §4.
- Nama tetap "BlackScan Lite" di UI agar tidak dikira Blockscout.

## 2. Arsitektur

```
Indexer (thread): poll eth_blockNumber tiap 2 dtk
  → eth_getBlockByNumber(n, full tx) + eth_getBlockReceipts(n)
  → SQLite: blocks, txs, meta(height)   [backfill dari blok 1, 50 blok/putaran]
Web/API (thread per request): baca SQLite + eth_getBalance live (alamat)
  + CometBFT /block?height= (proposer + app hash, lazy, di halaman blok)
```

- Blok EVM 0 adalah alias blok CometBFT 1 (keduanya mengembalikan hash
  `DBE87FE5…` dengan `number = 0x1`) — backfill dimulai dari blok 1.
- Finalitas instan CometBFT: tidak ada penanganan reorg (sesuai `docs/11` §2).

## 3. Uji (perintah + output nyata)

Semua uji 2026-11-20 ~17:35 UTC, setelah indexer mengejar head:

```
GET /api/v2/stats -> {"chain_id": 20261120, "blocks_indexed": 913,
  "transactions_indexed": 2, "indexed_height": 913,
  "avg_block_time_s": 5.63, "indexer_error": ""}
```

Transfer EVM yang sudah terbukti (Sesi 8, blok 6):

```
GET /api/v2/transactions/0x562cf1f23ebc3ef5e6b73df4111def7fa555a0321013b879880c38f5dde08350
-> {"block_number": 6, "from": "0x7c54d93649524ad774125a9e8e03b1bc1043238c",
    "to": "0xe85241d28a4e5837dc49586ac60158200e4596a9",
    "value_wei": "1000000", "status": "0x1", "gas_used": 21000}
GET /api/v2/blocks/6
-> {"number": 6, "hash": "0xc029becc11fafcedd934731792533be43ab2ca81373d0d602c609caf1f9a4f6f",
    "tx_count": 1, "miner": "0x4cbf51a8c10fff5e847e2d51b02c4b64714db174", ...}
```

Klaim faucet Sesi 12 (blok 829):

```
GET /api/v2/transactions/0x8dfe2e3c9b8aded52b03e6c85027cf60553143c320d4d99488a3558d0158e53c
-> {"block_number": 829, "value_wei": "100000000000000000000",
    "value_bkc": 100.0, "status": "0x1"}
```

Halaman HTML (dicek via curl + grep):
- `/` menampilkan "Blok terbaru" + "Transaksi terbaru" + hash `0x562cf1…`.
- `/block/6` menampilkan proposer `3D2A683F0CC46643A79802A598DE49ADB18A3698`
  dan app hash `1D4550477133361B3D50473058C5DBFC9CB38B5DBC8BDE71C27BB5CE52974970`
  (cocok dengan `curl 127.0.0.1:26777/block?height=6`).
- `/address/0x7C54…` menampilkan saldo live `9899.999987882526 BKC`.
- `/search?q=0x562cf1…` → halaman transaksi; `/search?q=829` → "Blok 829".

## 4. Bug yang ditemukan & diperbaiki saat pengujian (Sesi 12)

1. **Deadlock lock non-reentrant (F-baru? TIDAK — bug kode Sesi 12, diperbaiki
   sebelum rilis):** `_db_lock = threading.Lock()` tetapi endpoint
   `/api/v2/stats` memanggil `indexed_height()` (yang juga memakai lock)
   saat lock sedang dipegang → server menggantung total, indexer ikut
   membeku (0 blok). Perbaikan: `threading.RLock()`.
2. **Argumen RPC tertukar:** `rpc_call(url, method)` didefinisikan dengan
   `url` pertama tetapi dipanggil sebagai `rpc_call("eth_blockNumber")` —
   indexer gagal dengan `TypeError` dan me-retry selamanya. Perbaikan:
   `rpc_call(method, params=None, url=EVM_RPC)`.
3. **INSERT tx kelebihan 1 placeholder:** 13 `?` untuk 12 kolom —
   indexer error `table txs has 12 columns but 13 values were supplied`.
   Perbaikan: 12 placeholder.
4. **Blok 0 alias blok 1:** backfill kini mulai dari blok 1 (lihat §2).

Ketiga bug terjadi pada kode yang belum pernah jalan; semuanya diperbaiki
dan diverifikasi dengan angka di §3. Tidak ada kegagalan baru yang
dicatat sebagai F di mission log untuk bug internal sesi ini (kecuali
F34 insiden VM restart — lihat §5).

## 5. Insiden: VM/runtime restart mematikan semua proses (F34)

Selama Sesi 12 (2026-11-20 ~17:28 UTC), layanan eksekusi VM me-restart
dan **semua proses mati**: devnet BKC, 4 validator testnet, node fork
Phase 1 (Sesi 9), faucet, dan BlackScan (yang baru saja di-start).
Semua RPC tidak menjawab. Ini mengonfirmasi kerapuhan yang sudah
diketahui: proses node TIDAK bertahan melewati restart VM — butuh
systemd/supervisor + skrip restart (lihat `docs/24` §5 dan F34 di
mission log).

Pemulihan Sesi 12 (perintah + bukti):
- Skrip baru `scripts/restart-local-nodes.sh` (di luar repo) me-restart
  4 validator + devnet dari data disk yang sama (tanpa ubah config/home).
- Hasil: devnet height 10814; keempat validator height 853 dengan hash
  SAMA `E32209ED1314`, `catching_up: false` — konsensus pulih tanpa fork.
- Faucet di-restart: state klaim bertahan (`total_claims: 1`,
  saldo 9.899,9999 BKC — 100 BKC sudah tersalur sebelum restart).
- Node fork Phase 1 TIDAK di-restart oleh Sesi 12 (milik Sesi 9 yang
  masih berjalan — Sesi 9 yang mengurus nodenya sendiri).

## 6. Operasional

- Start: `cd repo/blackscan && ./start.sh` (atau nohup ke `blackscan.log`).
- Stop: kill PID `blackscan.py` berdasarkan PID (JANGAN `pkill -f blackscan.py`
  dari shell yang perintahnya sendiri mengandung string itu — pernah
  mematikan shell sendiri).
- Data: `repo/blackscan/data/blackscan.db` (SQLite WAL, di-gitignore).
  Hapus file DB untuk backfill ulang dari blok 1.
- Bila indexer tertinggal: cek `GET /api/health` (`indexed_height`,
  `indexer_error`).

## 7. Hal terbuka (butuh keputusan pemilik)

1. Blockscout penuh vs BlackScan Lite untuk testnet publik (biaya server +
   lisensi source-available Blockscout sejak April 2026 — `docs/11` §1).
2. Node RPC khusus untuk indexer (bukan node validator) + domain/hosting.
3. Verifikasi kontrak (BKC/TeamVesting/CommunityClaim) — butuh diputuskan
   bersama Blockscout penuh atau ditunda.
