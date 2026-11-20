# BLACKCHAIN — Developer Guide (DRAFT v0.1, 20 Nov 2026)

> **Status:** DRAFT. Belum ada jaringan yang bisa dihubungkan — panduan ini
> berlaku setelah devnet/testnet berjalan.

## 1. Membangun di Blackchain

Blackchain adalah EVM-compatible: semua tooling Ethereum bekerja tanpa
perubahan.

- **Wallet:** MetaMask (tambahkan jaringan Blackchain dengan RPC + chain ID
  yang diumumkan saat testnet; JANGAN percaya chain ID dari sumber tak resmi).
- **Framework:** Hardhat, Foundry, Truffle.
- **Library:** ethers.js, web3.js.
- **Kontrak:** Solidity — standar ERC-20, ERC-721, ERC-1155 didukung;
  kontrak OpenZeppelin dapat di-deploy tanpa perubahan (pola Ethermint).

## 2. Jaringan

| Jaringan | Status 20 Nov 2026 |
|---|---|
| Devnet lokal | Draft genesis tersedia; belum berjalan |
| Testnet publik | Belum diluncurkan (Month 2) |
| Mainnet | Belum diluncurkan |

## 3. RPC

- Ethereum JSON-RPC: port 8545 (HTTP), 8546 (WebSocket) — mengikuti pola
  Ethermint.
- Cosmos REST/gRPC: untuk query staking, governance, dan IBC.
- Endpoint resmi HANYA diumumkan lewat kanal resmi setelah testnet live.
  Endpoint yang beredar sebelum itu harus dianggap tidak resmi.

## 4. Faucet (testnet)

Faucet testnet akan disediakan di Month 2. Token testnet TIDAK bernilai dan
tidak dapat dipindah ke mainnet.

## 5. Aturan keamanan untuk developer

- Audit kontrak Anda sebelum deploy ke mainnet.
- Jangan hardcode private key di kode.
- Laporkan bug lewat program bug bounty (dibuka Month 3).
