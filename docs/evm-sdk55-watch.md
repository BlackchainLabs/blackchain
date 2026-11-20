# Cosmos EVM — Watch rilis untuk SDK v0.55 (Jalur B)

## Status terakhir dicek: 2026-11-20 13:45 UTC (20:45 WIB)
- Sumber: https://github.com/cosmos/evm/releases (dibuka langsung, crawl 13:45 UTC)
  + cek sebelumnya: 2026-11-20 12:30 UTC (hasil sama).
- GitHub REST API https://api.github.com/repos/cosmos/evm/releases pada 20 Nov 2026
  mengembalikan HTTP 403 rate limit exceeded (IP bersama) — API tidak bisa dipakai
  tanpa auth; halaman web dipakai sebagai gantinya.

## Versi terakhir yang dicek
- **v0.7.4** — terbaru. Security fixes, STATE BREAKING. Changelog v0.7.3...v0.7.4.
  Menarget Cosmos SDK **v0.54.3** (go.mod), api v1.0.0, CometBFT v0.39.3, ibc-go v11.
- v0.6.5 — JSON-RPC/indexer only, NOT state breaking (changelog v0.6.4...v0.6.5).
- v0.6.4, v0.7.3, v0.6.3, v0.7.2, v0.6.2, v0.7.1, v0.6.1, v0.7.0 (Krakatoa mempool,
  BlockSTM, ICS-02 client-router precompile, OTel tracing, JSON-RPC filter overhaul).

## Yang masih kurang (belum ada)
- **TIDAK ADA rilis Cosmos EVM yang menarget Cosmos SDK v0.55** per 20 Nov 2026.
- Tidak ada v0.8 / v0.7.5 / rilis lain di atas v0.7.4 pada halaman rilis.
- Jangan klaim rilis SDK v0.55 ada sebelum halaman rilis menunjukkannya.

## Yang harus dicek pada pengecekan ulang
1. Apakah ada rilis baru di atas v0.7.4 (v0.7.5 / v0.8.0 / lainnya)?
2. Buka go.mod rilis tersebut (atau changelog-nya): versi Cosmos SDK yang ditarget?
   Syarat lolos: `github.com/cosmos/cosmos-sdk v0.55.x` (atau lebih baru yang kompatibel).
3. Perhatikan juga catatan "state breaking" dan security fixes.

## Cek ulang berikutnya
- **27 Nov 2026** (1 minggu), atau lebih cepat bila ada pengumuman Cosmos EVM / SDK.
- Bila rilis SDK v0.55 sudah ada: evaluasi migrasi scaffold SDK 0.55 ke rilis itu
  (Jalur A tetap jalur EVM yang jalan sampai saat itu), dan perbarui file ini.

## Kaitan dengan jalur lain (20 Nov 2026)
- Jalur A (utama, SELESAI): scaffold SDK v0.54.5 + Cosmos EVM v0.7.4, EVM live,
  transfer EVM terbukti (lihat docs/cosmos-devnet-sdk54-first-blocks-2026-11-20.txt).
- Jalur C (SEBAGIAN): fork Cosmos EVM v0.7.4 + patch SIGN_MODE_TEXTUAL -> DIRECT.
  Patch inti lolos (x/vm/types build bersih di SDK 0.55), TAPI paket mempool fork
  tidak compile di SDK 0.55 (interface mempool berubah: Iterator.Tx() -> PooledTx).
  Lihat docs/evm-fork-patch-v0.7.4-sdk55.diff dan mission log (F18-F19).
