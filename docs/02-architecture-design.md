# BLACKCHAIN — Desain Arsitektur v0.1 (DRAFT, Month 1, 20 Nov 2026)

**Status:** DRAFT desain — belum ada kode node yang dikompilasi. Setiap angka
di bawah adalah **parameter desain yang diusulkan**, bukan hasil pengukuran.
**Penulis:** Chief Blockchain Architect AI + Consensus Research AI.

## 1. Identitas jaringan (diusulkan)

| Parameter | Nilai |
|---|---|
| Nama chain | Blackchain |
| Coin native | BKC |
| Chain ID Cosmos (devnet) | `blackchain-devnet-1` |
| EVM chain ID (devnet lokal) | `1337` (standar dev lokal; chain ID testnet publik dialokasikan setelah cek registry ethereum-lists/chains — JANGAN pakai 9000/9001 yang sudah dipakai Evmos) |
| Arsitektur | EVM Hybrid Layer 1 (Cosmos SDK + CometBFT + Ethermint) |
| Konsensus | BFT Proof of Stake (CometBFT) |
| Eksekusi | EVM (Ethermint, kompatibel go-ethereum) |
| Smart contract | Solidity (EVM bytecode) |
| Block time target (desain) | ~3 detik (mengikuti pola Cosmos/Ethermint; HARUS diukur di devnet, bukan diklaim) |
| Finalitas | Instan setelah quorum >2/3 voting power (sifat CometBFT) |
| Max supply | 1.000.000.000 BKC, 18 desimal |
| Dev network awal | Ethereum Sepolia — HANYA untuk kontrak pendukung (mis. vesting/claim diuji di Sepolia); BUKAN Blackchain itu sendiri |

## 2. Lapisan arsitektur

```
┌─────────────────────────────────────────────────────────┐
│  Aplikasi / Tooling: MetaMask, Hardhat, Foundry,        │
│  ethers.js, web3.js, Blockscout (BlackScan)             │
├─────────────────────────────────────────────────────────┤
│  JSON-RPC Ethereum (8545/8546) + Cosmos REST/gRPC       │
├─────────────────────────────────────────────────────────┤
│  Execution: x/evm (Ethermint) + x/feemarket (EIP-1559)  │
├─────────────────────────────────────────────────────────┤
│  Aplikasi Cosmos SDK: auth, bank, staking, gov,         │
│  distribution, slashing, ibc-go, x/blackchain (kustom)  │
├─────────────────────────────────────────────────────────┤
│  Konsensus: CometBFT (ABCI) — propose / prevote /       │
│  precommit, quorum >2/3, toleran <1/3 Byzantine          │
├─────────────────────────────────────────────────────────┤
│  Networking: CometBFT P2P + libp2p (EVM layer bila ada) │
│  Storage: CometBFT/ABCI app state (IAVL + EVM state)    │
└─────────────────────────────────────────────────────────┘
```

## 3. Desain konsensus & validator (diusulkan, perlu persetujuan governance)

- **Seleksi validator:** delegated PoS; N validator teratas berdasarkan total
  stake (self-stake + delegasi) masuk active set. N awal devnet: 4 (lokal),
  testnet publik: diusulkan 21–100 (keputusan final setelah load test).
- **Voting power** sebanding dengan stake; diusulkan cap 10% dari total stake
  per validator untuk mencegah sentralisasi (mengikuti praktik Surge; masih
  perlu diputuskan).
- **Proposer:** rotasi deterministik per height/round ala CometBFT.
- **Slashing (diusulkan):** double-sign (equivocation) dan liveness failure
  (miss block melewati ambang per epoch). Persentase slash dan periode
  unbonding (diusulkan 21 hari, mengikuti pola Cosmos) WAJIB diputuskan
  governance sebelum testnet publik — bukan keputusan sepihak AI.
- **Reward:** inflasi blok + fee; skema reward persisnya milik Tokenomics
  Research AI dan belum final di dokumen ini.

## 4. Desain tokenomics BKC (ringkasan, detail di `docs/04-tokenomics.md`)

- Max supply 1.000.000.000 BKC (1e9 × 1e18 = 1e27 unit terkecil).
- Komunitas 95% (950.000.000 BKC), tim dev 5% (50.000.000 BKC).
- Vesting tim 12 bulan, jadwal publik, claim contract transparan.
- Airdrop untuk partisipan testnet, validator, bug bounty, developer,
  kontributor — dengan anti-Sybil, tanpa mengecualikan partisipan sah
  secara arbitrer.
- Buyback & burn bulanan: HANYA dengan persetujuan governance; tidak ada
  transaksi treasury yang dieksekusi di misi ini.

## 5. Modul ekosistem

| Modul | Repo | Status 20 Nov 2026 |
|---|---|---|
| blockchain-core | `blockchain-core/` | Desain v0.1 ini; kode belum ditulis (butuh Go toolchain) |
| consensus | `consensus/` | Desain §3; parameter belum final |
| evm-engine | `evm-engine/` | Diputuskan: Ethermint |
| validator-node | `validator-node/` | Panduan operator: DRAFT di `docs/06-validator-guide.md` |
| black-wallet | `black-wallet/` | Spesifikasi fitur di whitepaper Bab 14; kode belum ada |
| blackswap | `blackswap/` | Spesifikasi fitur di whitepaper Bab 15; kode belum ada |
| blackbridge | `blackbridge/` | Desain keamanan di whitepaper Bab 16; TIDAK diluncurkan tanpa audit |
| blackscan | `blackscan/` | Diputuskan: Blockscout (pola NovaChain); belum di-deploy |
| smart-contracts | `smart-contracts/` | Kontrak vesting/claim: DRAFT spesifikasi, belum di-deploy ke Sepolia |
| tokenomics | `tokenomics/` | `docs/04-tokenomics.md` |
| testnet | `testnet/` | Genesis devnet: `genesis/blackchain-devnet-genesis.json` |

## 6. Keamanan (prinsip, bukan klaim)

- Unit test, integration test, fuzz test, property-based test — WAJIB sebelum
  testnet publik; belum ada yang berjalan hari ini.
- Audit independen WAJIB sebelum mainnet dan sebelum bridge tanpa batas.
- Tidak ada seed phrase / private key yang pernah diminta, disimpan, atau
  ditulis di dokumen mana pun dalam misi ini.
- Tidak ada kredensial infrastruktur yang dipublikasikan.

## 7. Apa yang BELUM benar (jujur)

1. Belum ada satu baris pun kode Go yang dikompilasi — Go toolchain TIDAK
   tersedia di VM ini (`which go` kosong). Ini kegagalan lingkungan yang
   dicatat di dev log; perbaikannya: jalankan langkah build di mesin dengan
   Go, atau instal Go di VM (dicoba, lihat dev log).
2. Belum ada devnet yang berjalan, belum ada blok yang dihasilkan.
3. Belum ada benchmark TPS apa pun. Target 100.000 TPS = target.
4. Genesis di `genesis/` adalah draft devnet lokal (go-ethereum format) untuk
   validasi format dan pengujian awal — BUKAN genesis final Cosmos dan BUKAN
   genesis testnet publik.
