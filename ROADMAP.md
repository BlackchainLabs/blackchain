# BLACKCHAIN — Roadmap (Testnet 3 Bulan)

**Status 20 Nov 2026:** Month 1 sedang berjalan (riset & desain selesai untuk
framework, arsitektur, tokenomics, genesis devnet). Month 2–3 belum dimulai.

## Month 1 — Core Development

- [x] Riset framework EVM L1 open-source (Cosmos SDK + CometBFT + Ethermint diputuskan)
- [x] Desain arsitektur v0.1 + desain konsensus
- [x] Draft genesis devnet (format go-ethereum, chain ID 1337 lokal)
- [x] Struktur repo + dokumen root
- [x] Draft whitepaper Bab 1–7; Bab 8–21 sebagai outline terstruktur
- [ ] Inisialisasi `blockchain-core` dari template Cosmos SDK + Ethermint
      — TERHAMBAT: Go toolchain tidak tersedia di VM misi; Go 1.27.4 berhasil
      diinstal 20 Nov 2026, build Geth sedang dicoba sebagai validasi
      lingkungan. Langkah ini butuh mesin build khusus.
- [ ] Devnet lokal 1–4 validator berjalan + log blok pertama
- [ ] Dokumentasi developer v0.1

## Month 2 — Public Testnet

- [ ] Public testnet (chain ID dialokasikan setelah cek registry)
- [ ] Validator onboarding
- [ ] Faucet
- [ ] BlackScan (explorer) live di testnet
- [ ] BlackSwap development
- [ ] Bridge test environment (tanpa aset nyata, tanpa batas transfer)

## Month 3 — Hardening & Mainnet Readiness

- [ ] Load testing (angka diukur dan dilaporkan per kategori: teoritis /
      laboratorium / sustained / finalized — TIDAK dikarang)
- [ ] Security audits (independen, wajib sebelum mainnet)
- [ ] Bug bounty
- [ ] Airdrop snapshot preparation
- [ ] Vesting validation
- [ ] Mainnet readiness assessment — keputusan launch oleh owner

## Jangka panjang

- Target 100.000 TPS (target, bukan klaim) via eksekusi paralel, scheduling
  transaksi yang efisien, storage state yang dioptimalkan, dan scaling
  validator — masing-masing dibuktikan dengan benchmark yang bisa
  direproduksi sebelum diklaim.
