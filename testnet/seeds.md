# BLACKCHAIN — Daftar Seed Node Testnet

**Status 20 Nov 2026 (Sesi 10): BELUM ADA SEED PUBLIK.**

## ⚠️ Peringatan — baca sebelum memakai daftar ini

Daftar di bawah ini adalah seed node dari **jaringan rehearsal 4 validator
yang hanya berjalan di satu VM lokal (127.0.0.1)**. Alamat-alamat ini
**TIDAK BISA dijangkau dari internet** dan **HANYA berlaku di dalam VM
tersebut**. Jangan mencoba terhubung ke alamat ini dari mesin lain —
koneksi akan gagal karena 127.0.0.1 selalu berarti "mesin sendiri".

Seed node publik yang sesungguhnya (node ID + IP publik + port 26656)
baru akan diterbitkan di file ini setelah VPS + IP publik tersedia
(prasyarat P1, `docs/18-testnet-launch-package.md` §7). Sampai saat itu,
file ini adalah TEMPAT PENAMPUNG yang jujur: isinya hanya node rehearsal
lokal, dengan label yang jelas.

## Seed node rehearsal (LOKAL SAJA — 127.0.0.1)

Chain: `blackchain_20261120-1` · EVM chain ID `20261120` (`0x1352900`) ·
denom `abkc`. Terverifikasi sinkron penuh 20 Nov 2026 ~16:52 UTC
(height 472, hash `C73E9F4189E6959D…` sama di keempat node —
`docs/17-testnet-multivalidator.md` §8).

| Validator | Node ID (P2P) | Alamat P2P (LOKAL) | Status saat Sesi 10 |
|---|---|---|---|
| val1 | `9088193266bf7fe1addf21ea42dfa8c5b3ff97a2` | `9088193266bf7fe1addf21ea42dfa8c5b3ff97a2@127.0.0.1:26776` | Live, height 472 |
| val2 | `1cc0f94349707b4f3a9ac8b69e3c40fec9010f32` | `1cc0f94349707b4f3a9ac8b69e3c40fec9010f32@127.0.0.1:26786` | Live, height 472 |
| val3 | `7e7320fa5271e2c9cec93ecb0dc74d495b1fc80e` | `7e7320fa5271e2c9cec93ecb0dc74d495b1fc80e@127.0.0.1:26796` | Live, height 472 |
| val4 | `fcae4c9ecb0a8635c7b2b1352d1ab8579e9bca84` | `fcae4c9ecb0a8635c7b2b1352d1ab8579e9bca84@127.0.0.1:26806` | Live, height 472 |

Catatan teknis: port P2P rehearsal adalah 26776/26786/26796/26806
(bukan 26656 default) karena empat node berbagi satu mesin. Node publik
nanti memakai port **26656** (lihat `docs/18` §5).

## Seed node publik (akan datang)

| Validator | Node ID (P2P) | Alamat P2P (publik) | Status |
|---|---|---|---|
| (belum ada) | — | — | Menunggu VPS + IP publik (P1) |

Format alamat seed publik nanti:
`<node-id>@<IP-publik>:26656` — dipakai sebagai `--p2p.seeds` saat
start node (lihat `testnet/README.md` langkah 4).
