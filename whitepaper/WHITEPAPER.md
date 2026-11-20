# BLACKCHAIN WHITEPAPER — DRAFT v0.1 (20 Nov 2026)

> **Status:** DRAFT. Bab 1–7 ditulis penuh. Bab 8–21 berupa outline terstruktur
> yang akan dilengkapi bertahap. Semua klaim teknis yang belum didukung
> implementasi ditandai sebagai desain/asumsi. Testnet dan mainnet BELUM live.
> Target 100.000 TPS adalah target jangka panjang, bukan hasil terukur.

---

## 1. Abstract

Blackchain adalah blockchain Layer 1 independen yang kompatibel dengan
Ethereum Virtual Machine (EVM), dibangun di atas Cosmos SDK dengan konsensus
CometBFT Byzantine Fault Tolerant Proof of Stake (BFT PoS) dan eksekusi
Ethermint. Coin native-nya adalah BKC dengan max supply 1.000.000.000 BKC
(95% komunitas, 5% tim, vesting 12 bulan).

Blackchain bertujuan memberi developer Ethereum pengalaman yang sudah mereka
kenal — Solidity, MetaMask, Hardhat, Foundry — di atas jaringan sovereign
dengan finalitas instan dan biaya rendah, tanpa bergantung pada settlement
Ethereum. Ekosistemnya mencakup Black Wallet (non-custodial), BlackSwap
(DEX), BlackBridge (cross-chain), dan BlackScan (explorer).

Dokumen ini adalah draft Month 1. Tidak ada bagian dari whitepaper ini yang
menjanjikan return investasi atau apresiasi harga token.

## 2. Introduction

Ethereum memiliki ekosistem developer terbesar di dunia, tetapi membangun
Layer 1 baru dari nol secara historis berarti menulis ulang konsensus,
networking, dan tooling — pekerjaan bertahun-tahun dengan risiko keamanan
besar. Framework modular modern mengubah persamaan itu: Cosmos SDK memberi
modul aplikasi siap pakai, CometBFT memberi konsensus BFT yang terbukti di
produksi, dan Ethermint memberi kompatibilitas EVM penuh.

Blackchain menggabungkan ketiganya. Hasilnya adalah jaringan yang independen
— konsensus, validator, genesis, eksekusi, RPC, dan explorer-nya sendiri —
tetapi tetap dapat menjalankan kontrak Solidity yang sudah ada tanpa modifikasi.

## 3. Problem Statement

1. **Fragmentasi:** developer harus memilih antara keamanan Ethereum dan
   kedaulatan chain sendiri.
2. **Biaya dan kecepatan:** jaringan EVM yang ramai membebankan fee tinggi
   dan konfirmasi lambat untuk aplikasi sehari-hari.
3. **Ketergantungan L2:** rollup menyelesaikan skalabilitas dengan
   mengorbankan kedaulatan — keamanan dan finalitasnya bergantung pada
   Ethereum.
4. **Distribusi token yang tidak adil:** banyak proyek mengalokasikan
   mayoritas supply untuk tim dan investor awal.
5. **Keamanan bridge:** bridge cross-chain adalah titik kegagalan yang
   paling sering dieksploitasi di industri ini.

## 4. Blackchain Vision

Satu jaringan Layer 1 yang independen, aman, dan scalable — dimiliki
mayoritas oleh komunitasnya (95%), dengan tata kelola transparan, dan
ekosistem lengkap (wallet, DEX, bridge, explorer) yang dibangun di atasnya.

Prinsip: bangun secara independen, skala secara bertanggung jawab, amankan
masa depan. Jangan berhenti di whitepaper atau kontrak token — bangun
perangkat lunak yang bekerja, uji, dokumentasikan, verifikasi keamanannya,
dan berikan instruksi deployment yang bisa direproduksi.

## 5. Network Architecture

Arsitektur v0.1 (detail lengkap di `docs/02-architecture-design.md`):

| Lapisan | Teknologi |
|---|---|
| Aplikasi | Cosmos SDK: auth, bank, staking, gov, distribution, slashing, IBC |
| Eksekusi | Ethermint EVM + feemarket EIP-1559 |
| Konsensus | CometBFT (ABCI) |
| Jaringan | CometBFT P2P |
| Tooling | MetaMask, Hardhat, Foundry, ethers.js, web3.js |

Keputusan framework didokumentasikan dengan sumber di
`docs/01-framework-research.md`: Cosmos SDK + CometBFT + Ethermint dipilih
karena merupakan satu-satunya kandidat yang memberi L1 independen + BFT PoS
+ EVM penuh tanpa menulis konsensus dari nol, dengan preceden produksi
(Evmos, Cronos, dYdX, Osmosis, Celestia).

Dev network awal adalah Ethereum Sepolia — hanya untuk menguji kontrak
pendukung (vesting/claim). Sepolia BUKAN Blackchain.

## 6. Consensus Mechanism

Blackchain memakai CometBFT, mesin konsensus BFT PoS (dulu Tendermint Core,
rebrand 2023). Mekanismenya:

- Untuk setiap height, validator menjalankan satu atau lebih round.
- Satu proposer mengusulkan blok; semua validator memberikan dua vote:
  **prevote** lalu **precommit**.
- Blok final begitu precommit dari **lebih dari 2/3 voting power**
  terkumpul. Finalitas instan — tidak ada konfirmasi menunggu, tidak ada
  fork/reorg.
- Sistem mentolerir sampai **kurang dari 1/3 voting power Byzantine**
  (crash, berbohong, atau kolusi).
- ABCI memisahkan mesin konsensus dari aplikasi, sehingga aplikasi dapat
  ditulis dalam bahasa apa pun.

Validator dipilih lewat delegated PoS: N validator teratas berdasarkan total
stake masuk active set. Parameter final (ukuran active set, self-stake
minimum, persentase slash, periode unbonding) diputuskan governance sebelum
testnet publik — diusulkan: active set 21–100, cap voting power 10% per
validator, unbonding 21 hari.

## 7. EVM Compatibility

Melalui modul Ethermint, Blackchain menjalankan EVM penuh:

- Kontrak Solidity dan Vyper dapat di-deploy tanpa modifikasi.
- Standar ERC-20, ERC-721, ERC-1155 didukung.
- Kontrak OpenZeppelin dapat di-deploy tanpa perubahan.
- MetaMask, Hardhat, Foundry, Truffle, ethers.js, dan web3.js bekerja.
- JSON-RPC Ethereum di port 8545 (HTTP) dan 8546 (WebSocket).
- Fee market EIP-1559 via modul `feemarket`.

Dua model akun (Cosmos bech32 dan Ethereum hex) dijembatani mengikuti pola
Evmos/Cronos — area ini membutuhkan pengujian khusus sebelum testnet publik.

---

## 8. Transaction Execution — OUTLINE (akan dilengkapi Month 1–2)

- Alur transaksi: mempool → proposer → eksekusi EVM → commit ABCI.
- Urutan eksekusi, gas metering (EIP-1559), dan penanganan revert.
- Eksekusi paralel sebagai riset jangka panjang (bukan klaim v1).
- **Status:** outline; butuh pengukuran nyata setelah devnet berjalan.

## 9. Validator Economics — OUTLINE

- Reward blok + fee; skema emisi per tahun BELUM diputuskan.
- Komisi validator, pembagian reward delegator, mekanisme slash.
- Cap voting power 10% (diusulkan).
- **Status:** outline; parameter final diputuskan governance.

## 10. BKC Tokenomics — DRAFT (lihat `docs/04-tokenomics.md`)

- Max supply 1.000.000.000 BKC; komunitas 95% (950.000.000), tim 5%
  (50.000.000); vesting tim 12 bulan.
- Usulan rincian komunitas: airdrop 200jt, reward validator 400jt,
  ekosistem/grants 200jt, bug bounty 50jt, cadangan DAO 100jt.
- **Status:** draft; rincian komunitas adalah usulan, bukan keputusan.

## 11. Community Airdrop — OUTLINE

- Kriteria: partisipan testnet, operator validator, peneliti bug bounty,
  developer, kontributor ekosistem, partisipasi komunitas genuine.
- Anti-Sybil: analisis pola on-chain + bukti kontribusi; skoring detail
  dirancang Month 2.
- **Status:** outline.

## 12. Vesting Mechanism — OUTLINE

- Vesting tim 12 bulan, cliff 3 bulan (diusulkan), claim contract transparan,
  jadwal publik di dashboard supply.
- Kontrak vesting BELUM di-deploy; spesifikasi dan audit mendahului deploy
  ke Sepolia.
- **Status:** outline.

## 13. Buyback and Burn — OUTLINE (aturan, bukan eksekusi)

- Laporan keuangan bulanan, monitoring treasury, kebijakan buyback yang
  disetujui, catatan eksekusi transparan, transaksi burn yang dapat
  diverifikasi, review treasury independen.
- Tidak ada janji apresiasi harga. Tidak ada eksekusi tanpa persetujuan
  governance.
- **Status:** outline; tidak ada transaksi yang dieksekusi.

## 14. Black Wallet — OUTLINE

- Wallet non-custodial mandiri: create/import wallet, mnemonic generation
  yang aman, enkripsi private key, saldo BKC, kirim/terima, QR code, riwayat
  transaksi, manajemen token, network switching, address book, integrasi
  hardware wallet, kompatibilitas WalletConnect bila sesuai.
- Seed phrase / private key TIDAK PERNAH dikirim ke server AI.
- **Status:** spesifikasi fitur; kode belum ada.

## 15. BlackSwap — OUTLINE

- DEX: token swap, liquidity pool, manajemen LP, slippage protection,
  perhitungan price impact, riwayat trading, analitik pool, proteksi MEV
  bila secara teknis memungkinkan.
- **Status:** spesifikasi fitur; kode belum ada.

## 16. BlackBridge — OUTLINE

- Target: Ethereum, BNB Chain, Base, Solana, dan jaringan EVM lain yang
  disetujui.
- Verifikasi pesan cross-chain, keamanan validator, rate limit, monitoring
  transaksi, emergency pause, replay protection, audit bridge independen.
- **Tidak diluncurkan tanpa audit dan tanpa batas transfer.**
- **Status:** outline desain keamanan; kode belum ada.

## 17. Security Architecture — OUTLINE

- Unit test, integration test, fuzz testing, property-based testing,
  simulasi serangan konsensus, audit smart contract, audit bridge, dependency
  scanning, supply-chain security, threat modeling validator, disaster
  recovery.
- Persetujuan keamanan independen wajib sebelum mainnet.
- **Status:** outline; belum ada test yang berjalan (20 Nov 2026).

## 18. Governance — OUTLINE

- AI dapat autonom: riset, tulis kode, buat test, review kode, perbaiki bug
  non-destruktif, siapkan PR, perbarui dokumentasi, monitor testnet, buat
  laporan performa.
- Persetujuan manusia wajib: mainnet launch, transaksi treasury, distribusi
  token, buyback, burn, perubahan kebijakan slashing, upgrade protokol,
  manajemen kunci, registrasi akun, publikasi pengumuman resmi.
- **Status:** outline; mekanisme voting on-chain dirancang Month 2.

## 19. Roadmap — DRAFT (lihat `ROADMAP.md`)

- Month 1: core development, genesis, kontrak Sepolia, wallet awal, dokumentasi.
- Month 2: testnet publik, validator onboarding, faucet, explorer, swap,
  bridge test environment.
- Month 3: load testing, audit keamanan, bug bounty, persiapan snapshot
  airdrop, validasi vesting, penilaian kesiapan mainnet.
- **Status:** Month 1 berjalan; Month 2–3 belum dimulai.

## 20. Risk Disclosure

- **Risiko teknis:** bug konsensus, bug EVM, kegagalan bridge, serangan
  validator.
- **Risiko ekonomi:** volatilitas BKC, likuiditas rendah di awal, insentif
  validator yang belum teruji.
- **Risiko regulasi:** peraturan aset kripto berubah-ubah di tiap yurisdiksi.
- **Risiko eksekusi:** target 100.000 TPS mungkin tidak tercapai dengan
  sumber daya yang tersedia; bila demikian, keterbatasan dijelaskan dan
  alternatif terukur diusulkan.
- Dokumen ini bukan penawaran investasi dan bukan nasihat keuangan.

## 21. Technical References

1. Cosmos SDK — https://docs.cosmos.network (framework aplikasi modular)
2. CometBFT — https://docs.cometbft.com (konsensus BFT, dulu Tendermint Core)
3. Evmos / Ethermint — https://evmos.org (modul EVM untuk Cosmos SDK)
4. Cronos — https://deepwiki.com/crypto-org-chain/cronos (preceden produksi Cosmos SDK v0.54.3 + CometBFT v0.39.4 + Ethermint)
5. Binance Academy, "Tendermint Explained" — https://academy.binance.com/pl/articles/tendermint-explained
6. Optimism, "Best Rollup Frameworks for Launching an Ethereum L2" — https://optimism.io/blog/best-rollup-frameworks-for-launching-an-ethereum-l2 (alasan penolakan pendekatan L2)
7. Ethereum execution client measurements (ethpandaops, 1 Feb 2026) — https://gist.github.com/reldothescribe/579cae99cb48f56027c05588de9dcffb
8. YoChain Whitepaper v1.0 — https://www.yochain.network/YoChain_Whitepaper.pdf
9. NovaChain Whitepaper v1.0 — https://novachain.network/whitepaper.pdf

*Akhir draft v0.1 — 20 Nov 2026.*
