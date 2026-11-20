# BlackScan Lite v0.1 (Sesi 12)

Explorer minimal yang **benar-benar jalan** melawan rehearsal testnet lokal
(4 validator, EVM JSON-RPC val1 `127.0.0.1:8655`, CometBFT RPC `127.0.0.1:26777`,
chain ID 20261120).

**BUKAN Blockscout.** Blockscout penuh (Elixir + PostgreSQL 17 + archive node,
`docs/11`) terlalu berat untuk VM ini (1,5 CPU) dan untuk rantai ~900 blok.
Yang dibangun: indexer ringan Python stdlib + SQLite + halaman web sederhana.

## Menjalankan

```bash
./start.sh            # bind 127.0.0.1:8081
```

Stdlib Python saja — tanpa dependensi. Indexer backfill dari blok 1 lalu
mengikuti head (poll 2 detik). Data di `data/blackscan.db` (di-gitignore).

## Fitur

- Beranda: blok terbaru + transaksi terbaru + statistik + lag indexer.
- Detail blok: hash, parent, waktu, proposer CometBFT, app hash, gas, daftar tx.
- Detail transaksi: status, blok, dari/ke, nilai, gas, nonce, input.
- Alamat: saldo live (via `eth_getBalance`) + riwayat tx.
- Pencarian: hash tx (66 karakter), alamat 0x (42 karakter), nomor blok.
- API JSON minimal gaya Blockscout `/api/v2`:
  `blocks`, `blocks/<n>`, `transactions`, `transactions/<hash>`,
  `addresses/<addr>`, `addresses/<addr>/transactions`, `stats`, `search?q=`,
  plus `/api/health`.

## Uji (Sesi 12, 2026-11-20)

- 913 blok ter-index, 2 transaksi, lag 0, `indexer_error` kosong,
  waktu blok rata-rata 5,63 detik.
- Tx Sesi 8 `0x562cf1…` (blok 6, +1.000.000 wei) tampil benar di API + UI.
- Tx faucet `0x8dfe2e3c…` (blok 829, 100 tBKC) tampil benar di API + UI.
- Blok 6: proposer `3D2A683F0CC46643A79802A598DE49ADB18A3698`,
  app hash `1D455047…` (cocok dengan CometBFT).
- Detail lengkap: `docs/23-blackscan-implementation.md`.
