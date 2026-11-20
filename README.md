<p align="center"><img src="logo.jpg" width="220" alt="Logo BLACKCHAIN"></p>

# BLACKCHAIN

**Independent, secure, scalable EVM-compatible Hybrid Layer 1 blockchain.**
Native coin: **BKC** — max supply 1,000,000,000 BKC (95% community / 5% team, 12-month vesting).

> **Status jujur (20 Nov 2026):** Proyek dalam tahap Month 1 — riset & desain.
> Testnet dan mainnet **BELUM diluncurkan**. Belum ada node yang berjalan.
> Target 100.000 TPS adalah **target jangka panjang, bukan hasil terukur**.

## 🕹️ Pac-Man — jalan-jalan terus

![Pac-Man berjalan memakan titik](pacman.svg)

Pac-Man kami jalan-jalan terus di halaman ini, memakan titik tanpa henti.
Mau main sendiri? Buka **[pacman.html](pacman.html)** — game Pac-Man lengkap:
mode demo otomatis, 4 hantu, titik besar pemburu hantu, skor, nyawa, dan level.
Kendali: tombol panah / WASD, Spasi untuk mulai ulang.

## ⚡ Pikachu vs Kung Fu Panda — battle motion

![Pikachu melawan Kung Fu Panda](pikachu-vs-kungfu-panda.svg)

Petir kuning melawan Pendekar Naga! Buka **[pikachu-vs-kungfu-panda.html](pikachu-vs-kungfu-panda.html)**:
arena fighting dengan animasi gerak penuh — Pikachu melompat, Quick Attack, dan
Thunderbolt ⚡ melawan Panda Palm dan Dragon Spin 🐼 Po. Ada bar HP & energi,
timer 60 detik, hitung kemenangan, efek partikel, screen shake, dan suara.
Kendali: **A/D** gerak, **W** lompat, **J** pukul, **K** Thunderbolt.
Malas main? Nyalakan **demo otomatis** dan tonton mereka bertarung sendiri.

## Architecture (v0.1, proposed)

- **Application layer:** Cosmos SDK (modular: auth, bank, staking, gov, distribution, slashing, IBC)
- **Consensus:** CometBFT — BFT Proof of Stake, instant finality at >2/3 voting power quorum
- **Execution:** Ethermint EVM (go-ethereum compatible), EIP-1559 fee market
- **Smart contracts:** Solidity
- **Dev network:** Ethereum Sepolia (supporting contracts only — Sepolia is NOT Blackchain)

Full research and decision record: `docs/01-framework-research.md` and
`docs/02-architecture-design.md` (in the mission workspace).

## Repository layout

```
blackchain/
├── blockchain-core/   # Cosmos SDK app (app.go, modules)
├── consensus/         # CometBFT config, validator set design
├── evm-engine/        # Ethermint EVM integration
├── validator-node/    # Validator software & operator guide
├── black-wallet/      # Non-custodial wallet
├── blackswap/         # DEX: swaps, pools, LP management
├── blackbridge/       # Cross-chain bridge (NEVER launch unaudited)
├── blackscan/         # Block explorer (Blockscout-based)
├── smart-contracts/   # Solidity: vesting, claim, airdrop
├── tokenomics/        # BKC economics, vesting schedules
├── documentation/     # Developer & validator guides
├── whitepaper/        # 21-chapter whitepaper
├── infrastructure/    # RPC, monitoring, deployment
├── security/          # Audits, threat models, bug bounty
└── testnet/           # Genesis, faucet, testnet configs
```

## Documents

- `WHITEPAPER.md` — 21 chapters (draft in progress)
- `ROADMAP.md` — 3-month testnet plan
- `TOKENOMICS.md` — BKC allocation & vesting
- `VALIDATOR_GUIDE.md` — how to run a validator (draft)
- `DEVELOPER_GUIDE.md` — how to build on Blackchain (draft)
- `SECURITY.md` — vulnerability reporting
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `LICENSE`

## Governance — human approval required

The AI may autonomously research, write code, generate tests, review code,
fix non-destructive bugs, prepare pull requests, update docs, monitor testnet,
and produce performance reports.

**Human (owner) approval is mandatory for:** production mainnet launch,
treasury transactions, token distribution, buybacks, burns, validator
slashing policy changes, protocol upgrades, key management, account
registration, and external publication of official announcements.

## Security

Never send seed phrases or private keys to anyone, including the AI.
See `SECURITY.md`.
