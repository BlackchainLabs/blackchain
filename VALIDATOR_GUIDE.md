# BLACKCHAIN — Validator Guide (DRAFT v0.1, 20 Nov 2026)

> **Status:** DRAFT. Belum ada software validator yang bisa diinstal —
> panduan ini mendeskripsikan rencana operasional berdasarkan desain
> konsensus CometBFT/Cosmos SDK. Semua angka adalah usulan, bukan aturan
> final.

## 1. Peran validator

Validator mengusulkan dan menandatangani blok, mengamankan jaringan dengan
stake BKC, dan mendapat reward. Voting power sebanding dengan total stake
(self-stake + delegasi).

## 2. Persyaratan yang diusulkan (belum final)

| Item | Usulan |
|---|---|
| Active set testnet | 21–100 validator teratas berdasarkan stake |
| Self-stake minimum | Belum diputuskan (butuh keputusan governance) |
| Cap voting power | 10% dari total stake per validator (diusulkan) |
| Unbonding period | 21 hari (diusulkan, mengikuti pola Cosmos) |
| Komisi | Dapat dikonfigurasi operator; rentang wajar diputuskan governance |
| Hardware awal (devnet) | 4 CPU, 16 GB RAM, 500 GB NVMe SSD, koneksi stabil — estimasi kasar, HARUS diukur saat load test |

## 3. Slashing (diusulkan — wajib diputuskan governance sebelum testnet publik)

- **Double-sign (equivocation):** slash + tombstone (validator dikeluarkan
  permanen dari active set).
- **Liveness failure:** melewati ambang miss block per epoch → slash kecil
  + jail sementara.
- Persentase slash yang tepat BELUM diputuskan.

## 4. Langkah operasional (setelah software tersedia)

1. Instal `blackchaind` (binary validator-node) dari rilis resmi.
2. Inisialisasi node: `blackchaind init <moniker> --chain-id <chain-id>`.
3. Buat kunci validator (disimpan LOKAL, tidak pernah dikirim ke siapa pun,
   termasuk AI).
4. Daftarkan validator dengan `create-validator` + self-stake.
5. Jalankan node dengan monitoring (metrics Prometheus + alerting).
6. Jaga uptime; downtime berkepanjangan memicu liveness slashing.

## 5. Keamanan kunci

- Kunci validator TIDAK SAMA dengan seed phrase wallet.
- Gunakan HSM / remote signer bila memungkinkan.
- Jangan pernah membagikan private key atau mnemonic kepada siapa pun.
