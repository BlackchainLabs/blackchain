# BLACKCHAIN — Riset Framework EVM Layer 1 (Month 1, 20 Nov 2026)

**Status:** SELESAI (riset) — keputusan arsitektur diusulkan, belum diimplementasikan sebagai node.
**Penulis:** Consensus Research AI + Chief Blockchain Architect AI (dikerjakan 20 Nov 2026)
**Sumber:** hasil pencarian web 20 Nov 2026, diverifikasi dari sumber publik di bawah.

## 1. Tujuan

Menemukan framework open-source yang cocok untuk membangun BLACKCHAIN sebagai
**independent Layer 1 EVM-compatible** dengan konsensus **BFT Proof of Stake** —
bukan L2/rollup yang settle ke Ethereum, dan bukan sekadar token ERC-20 di Sepolia.

## 2. Kandidat yang dievaluasi

| Framework | Jenis | Konsensus | EVM | Cocok untuk L1 independen? |
|---|---|---|---|---|
| **Cosmos SDK + CometBFT + Ethermint (Evmos)** | Framework L1 modular | CometBFT BFT PoS, finalitas instan (quorum >2/3 voting power) | Penuh, via modul EVM Ethermint | **YA — rekomendasi** |
| OP Stack | Rollup framework (L2) | Optimistic, fault proof, challenge window ~7 hari | Ekuivalen penuh | TIDAK — settle ke Ethereum L1, bukan L1 independen |
| Arbitrum Orbit / Nitro | Rollup framework (L2/L3) | Optimistic / AnyTrust | Ekuivalen penuh + Stylus | TIDAK — settle ke Ethereum / Arbitrum |
| Polygon CDK | Rollup framework (L2) | ZK validity proof | Hampir penuh, ada edge case | TIDAK — L2, bukan L1 independen |
| ZK Stack (zkSync) | Rollup framework (L2) | ZK validity proof | Hampir penuh, ada edge case | TIDAK — L2, bukan L1 independen |
| Go-Ethereum (Geth) standalone + konsensus sendiri | Execution client | Harus dibangun sendiri / IBFT-QBFT via Besu | Penuh | MUNGKIN — tapi konsensus & staking harus ditulis dari nol, risiko dan waktu jauh lebih besar |
| Hyperledger Besu | Execution client | IBFT 2.0 / QBFT (BFT) | Penuh | MUNGKIN — cocok untuk jaringan permissioned/privat, kurang modul staking/IBC siap pakai |

## 3. Bukti pendukung

- **Evmos** adalah L1 PoS EVM-compatible yang dibangun dengan Cosmos SDK dan
  Tendermint Core (kini CometBFT); Ethermint adalah library open-source yang
  memungkinkan chain Cosmos SDK menjalankan EVM.
  Sumber: https://thecryptoblunt.com/explained/what-is-evmos-ecosystem/
- **Cronos** (Crypto.org) berjalan di Cosmos SDK v0.54.3 + CometBFT v0.39.4,
  dengan modul `ethermint/evm` dan `feemarket`, plus JSON-RPC Ethereum.
  Sumber: https://deepwiki.com/crypto-org-chain/cronos
- **YoChain** (2026) dan **NovaChain** (2026) adalah contoh L1 EVM baru yang
  memakai pola yang sama: Cosmos SDK + CometBFT + Ethermint, block time ~3 detik,
  finalitas instan, IBC.
  Sumber: https://www.yochain.network/YoChain_Whitepaper.pdf dan
  https://novachain.network/whitepaper.pdf
- **CometBFT** (dulu Tendermint Core, rebrand 2023): BFT PoS, satu validator
  diusulkan per ronde, blok final begitu >2/3 voting power menandatangani
  (prevote + precommit); toleran sampai <1/3 voting power Byzantine; tidak ada
  fork/reorg; ABCI memisahkan konsensus dari aplikasi sehingga aplikasi bisa
  ditulis dalam bahasa apa pun.
  Sumber: https://academy.binance.com/pl/articles/tendermint-explained
- **Rollup frameworks** (OP Stack, Orbit, CDK, ZK Stack) menangani mayoritas
  peluncuran L2 baru, tetapi semuanya settle ke Ethereum — bertentangan dengan
  misi L1 independen BLACKCHAIN.
  Sumber: https://optimism.io/blog/best-rollup-frameworks-for-launching-an-ethereum-l2
- **Execution client:** pada pengukuran ethpandaops 1 Feb 2026 (7.181 slot),
  rata-rata validasi blok `engine_newPayload`: Reth ~50 ms, Nethermind ~53 ms,
  Geth ~78 ms, Besu ~158 ms, Erigon ~250 ms. Angka ini adalah pengukuran
  Ethereum mainnet, BUKAN benchmark Blackchain.
  Sumber: https://gist.github.com/reldothescribe/579cae99cb48f56027c05588de9dcffb

## 4. Keputusan (diusulkan)

**Stack v1 BLACKCHAIN: Cosmos SDK + CometBFT + Ethermint (pola Evmos/Cronos).**

Alasan:
1. Satu-satunya kandidat yang memberi L1 independen + BFT PoS + EVM penuh
   tanpa menulis konsensus dari nol.
2. Modul siap pakai: `auth`, `bank`, `staking`, `gov`, `distribution`,
   `slashing`, `ibc-go`, `x/evm`, `x/feemarket` (EIP-1559).
3. Preceden produksi nyata (Evmos, Cronos, dYdX, Osmosis, Celestia memakai
   Cosmos SDK/CometBFT).
4. Bahasa utama Go — sesuai peran Senior Go Engineer AI; Rust dipakai untuk
   komponen performa (mis. tooling/benchmark), bukan untuk menulis ulang
   konsensus di v1.

**Yang TIDAK diputuskan di sini:**
- Versi pin Cosmos SDK / CometBFT / Ethermint (dipilih saat `go.mod` pertama
  dibuat, dari rilis stabil terbaru saat itu; TIDAK dikarang di dokumen ini).
- Angka TPS apa pun. Target 100.000 TPS tetap target jangka panjang, tanpa
  klaim terukur. CometBFT sendiri didokumentasikan menangani 1.000–10.000 TPS
  (Binance Academy) — itu angka literatur, bukan hasil Blackchain.

## 5. Risiko yang dicatat

- Ethermint adalah dependensi yang perawatannya bergantung pada komunitas
  Evmos; perlu dipin versinya dan dipantau.
- Cosmos SDK + EVM berarti dua model akun (Cosmos `bech32` + Ethereum `hex`)
  yang harus dijembatani dengan benar (pola `x/cronos` CRC21 / Evmos).
- Validasi performa nyata hanya bisa dilakukan setelah devnet berjalan —
  belum ada test yang bisa dijalankan hari ini untuk klaim performa.

## 6. Langkah berikut

1. Inisialisasi repo `blockchain-core` dari template Cosmos SDK + Ethermint
   (butuh Go toolchain — TIDAK tersedia di VM ini, lihat dev log).
2. Tulis `app.go` + genesis `blackchain-1` (draft genesis devnet ada di
   `genesis/blackchain-devnet-genesis.json`).
3. Jalankan devnet lokal 1–4 validator dan catat log sebagai bukti nyata.
