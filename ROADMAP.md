# BLACKCHAIN — Roadmap (Testnet 3 Bulan)

**Status 20 Nov 2026, 22:19 WIB:** Month 1 SELESAI dan terbukti. EVM live via
Jalur A, repo sudah live di GitHub. Sesi lanjutan sedang berjalan: penyelarasan
denom/chain-ID ke BKC, benchmark TPS terukur, dan kontrak vesting/claim.

> Prinsip: tidak ada angka yang dikarang. TPS, testnet, dan mainnet hanya
> diklaim bila ada bukti pengukuran / node yang berjalan.

## Month 1 — Core Development ✅ SELESAI

- [x] Riset framework EVM L1 open-source (Cosmos SDK + CometBFT + Ethermint diputuskan)
- [x] Desain arsitektur v0.1 + desain konsensus (BFT PoS, target block time ~3 detik)
- [x] Draft genesis devnet (chain ID 1337 lokal; alokasi 61.000.000 BKC placeholder)
- [x] Struktur repo + dokumen root (15 modul + 10 dokumen root)
- [x] Draft whitepaper Bab 1–7 penuh; Bab 8–21 outline terstruktur
- [x] Inisialisasi `blockchain-core` dari template Cosmos SDK — SELESAI 20 Nov 2026
      (Ignite scaffold, Cosmos SDK v0.55.0, `go build ./...` lolos, binary 184 MB,
      `go test ./x/blackchain/...` lolos)
- [x] Devnet lokal 1 validator berjalan + log blok pertama
      (chain `blackchain-1`, blok pertama height 1, mencapai height 139,
      blok ~5 detik, RPC localhost:26657)
- [x] Validasi otomatis 21/21 lolos + uji live Geth v1.17.10
      (`net_version` 1337, saldo 3 alamat placeholder cocok)
- [x] Dokumentasi developer v0.1 (VALIDATOR_GUIDE, DEVELOPER_GUIDE, SECURITY)

## EVM — Jalur A ✅ LIVE (di luar rencana Month 1 awal)

- [x] Scaffold ulang ke Cosmos SDK v0.54.5 + Cosmos EVM v0.7.4
      (v0.54.3 retracted upstream karena bug feegrant; dipakai v0.54.5)
- [x] Devnet EVM live: chain `blackchain-1`, height 128, blok ~5 detik,
      JSON-RPC 127.0.0.1:8545 (`eth_chainId` 0x40000, `eth_blockNumber` 0x80)
- [x] Transfer EVM pertama TERBUKTI: tx `0xd836e930…`, receipt blok 6,
      status 0x1, gas 21000, penerima +1.000.000 wei
- [x] Jalur B selesai: TIDAK ADA rilis Cosmos EVM untuk SDK v0.55
      (dicek 2x, 20 Nov 2026; cek ulang 27 Nov 2026)
- [x] Jalur C sebagian: patch SIGN_MODE_TEXTUAL → DIRECT menghilangkan
      error TEXTUAL, tapi fork mentok di 11 error mempool SDK 0.55 —
      bukan jalur utama; Jalur A tetap yang jalan
- [ ] Penyelarasan denom/chain-ID EVM ke BKC — SEDANG DIKERJAKAN
      (saat ini 262144/stake; diputuskan chain ID + denom final)

## GitHub ✅ LIVE

- [x] Akun GitHub Blackchain-dot (blackchainglobal6@gmail.com, 20 Nov 2026 21:11 WIB)
- [x] Organisasi BlackchainLabs (Free, 1 anggota) + repo publik BlackchainLabs/blackchain
- [x] Kode ter-push 20 Nov 2026 21:51 WIB (commit GitHub `f290cbe8`, 38 file)
      + logo.jpg (commit `a9487cd`, 21:52 WIB) — total 3 commit, 39 file
- [x] Logo BLACKCHAIN sebagai foto profil akun + avatar organisasi
- [x] Bonus arcade di repo: Pac-Man Neon + Pikachu vs Kung Fu Panda
      (game HTML playable + animasi SVG di README)

## Month 2 — Public Testnet (berikutnya)

- [ ] Public testnet (chain ID dialokasikan setelah cek registry — bukan 9000/9001)
- [ ] Parameter validator final: active-set, minimum self-stake, slash %, emisi reward
- [ ] Benchmark TPS terukur — SEDANG DIKERJAKAN (harness load test transaksi EVM nyata;
      target 100.000 TPS; bila gagal, pendekatan diubah sampai ada angka terukur —
      TIDAK dikarang)
- [ ] Kontrak vesting/claim (Solidity + unit test) — SEDANG DIKERJAKAN
      (deploy Sepolia butuh persetujuan eksplisit pemilik)
- [ ] Validator onboarding
- [ ] Faucet
- [ ] BlackScan (explorer) live di testnet
- [ ] BlackSwap development
- [ ] Bridge test environment (tanpa aset nyata, tanpa batas transfer)

## Month 3 — Hardening & Mainnet Readiness

- [ ] Load testing final (angka diukur dan dilaporkan per kategori: teoritis /
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
