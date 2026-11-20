# BLACKCHAIN — Roadmap (Testnet 3 Bulan)

**Status 20 Nov 2026, 22:49 WIB:** Month 1 SELESAI dan terbukti. EVM live via
Jalur A (chain ID 20261120, denom abkc), repo sudah live di GitHub (head
`fb547c42`). Sesi 7 selesai: tiga keputusan pemilik diwujudkan — insentif
validator hibrida, vesting multisig+timelock, arsitektur TPS Fase 1→4
disetujui + desain implementasi Fase 1. Testnet BELUM SIAP dibuka.

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
- [x] Penyelarasan denom/chain-ID EVM ke BKC — SELESAI Sesi 4
      (chain ID 20261120, denom `abkc`, transfer pertama terbukti)

## GitHub ✅ LIVE

- [x] Akun GitHub Blackchain-dot (blackchainglobal6@gmail.com, 20 Nov 2026 21:11 WIB)
- [x] Organisasi BlackchainLabs (Free, 1 anggota) + repo publik BlackchainLabs/blackchain
- [x] Kode ter-push 20 Nov 2026 21:51 WIB (commit GitHub `f290cbe8`, 38 file)
      + logo.jpg (commit `a9487cd`, 21:52 WIB) — total 3 commit, 39 file
- [x] Logo BLACKCHAIN sebagai foto profil akun + avatar organisasi
- [x] Bonus arcade di repo: Pac-Man Neon + Pikachu vs Kung Fu Panda
      (game HTML playable + animasi SVG di README)

## Month 2 — Public Testnet (berikutnya)

- [ ] Public testnet (chain ID 20261120 SUDAH dialokasikan setelah cek registry — bukan 9000/9001; yang kurang: server + IP publik + domain + tanggal buka + pengumuman, lihat `docs/18-testnet-launch-package.md` §7)
- [x] Parameter validator final — SELESAI Sesi 4 + Sesi 7: active-set maks 100, self-stake 1.000 BKC, slash double-sign 5% / downtime 1%, insentif hibrida (subsidi testnet 10 tBKC/blok, pagu 20 jt tBKC; mainnet fee + 50% fee protokol BlackSwap)
- [x] Benchmark TPS terukur — SELESAI Sesi 4 (maks ~89 TPS sustained, 0 tx gagal;
      bottleneck ingest ~110 tx/detik + blok ~1 detik + eksekusi serial;
      100.000 TPS tetap TARGET, jarak ~1.100×; laporan `docs/09-benchmark-tps.md`)
- [x] Jalur ke 100.000 TPS — RISET & DESAIN SELESAI Sesi 6 (`docs/10-tps-architecture-path.md`):
      rekomendasi ingest paralel + hardware dulu, lalu eksekusi paralel Block-STM;
      plafon tahap 1 ESTIMASI 300–1.000 TPS; urutan Fase 1→4 DISETUJUI pemilik Sesi 7
      dan desain implementasi Fase 1 selesai (`docs/16-phase1-ingest-design.md`);
      implementasi kode BELUM dimulai (sesi berikutnya)
- [x] Kontrak vesting/claim (Solidity + unit test) — SELESAI Sesi 4–5
      (OpenZeppelin v5.7.0, `forge test` 37/37 lolos); rencana deploy Sepolia
      SELESAI Sesi 7 (`docs/15-vesting-deployment-plan.md`): owner = multisig
      3-of-5 + timelock 48 jam DIPUTUSKAN; deploy menunggu alamat beneficiary/
      multisig + timestamp `start` (PLACEHOLDER, wajib diisi pemilik)
- [x] Spesifikasi BlackScan v0.1 — SELESAI Sesi 6 (`docs/11-blackscan-spec.md`;
      Blockscout, API /api/v2; implementasi & deploy BELUM)
- [x] Spesifikasi BlackSwap v0.1 — SELESAI Sesi 6 (`docs/12-blackswap-spec.md`;
      AMM x·y=k, fee 0,30%; kontrak, test & audit BELUM)
- [x] Spesifikasi faucet + panduan onboarding validator — SELESAI Sesi 6
      (`docs/13-faucet-validator-onboarding.md`; implementasi BELUM)
- [x] Checklist kesiapan testnet v0.1 — SELESAI Sesi 6, direvisi Sesi 7–8 (`docs/14-testnet-readiness.md`):
      rehearsal 4 validator TERBUKTI jalan; 13 siap / 6 sebagian / 8 belum /
      1 diblokir komunikasi; 4 hal konkret tersisa: alamat vesting, anggaran
      hardware, keputusan genesis final + tanggal buka, pengumuman
- [x] Testnet rehearsal multi-validator — SELESAI Sesi 8 (`docs/17-testnet-multivalidator.md`):
      4 validator live di VM lokal (height + hash sama di 4 node, 3 peer
      tiap node), transfer EVM terkonfirmasi di 4 node (tx `0x562cf1f2…`,
      blok 6, +1.000.000 wei), liveness 3/4 terbukti (val4 mati → blok
      7→10; restart → catch-up ke height 15). Kegagalan F32 (duplicate IP)
      + F33 (3 validator setara tidak bisa liveness 2/3) diperbaiki.
      INI REHEARSAL, BUKAN testnet publik (semua 127.0.0.1).
- [x] Genesis testnet (draft) — SELESAI Sesi 8 (`genesis/blackchain-testnet-genesis.json`):
      4 gentx @ 1.000 BKC, total supply genesis 30.080.000 BKC
      (pool subsidi 20 jt + faucet 10 jt dipegang alamat operator val1
      selama rehearsal — WAJIB dipindah sebelum publik), `genesis validate`
      LOLOS. Keputusan final (pakai vs buat ulang) + tanggal buka masih
      menunggu pemilik.
- [x] Paket peluncuran testnet — SELESAI Sesi 8 (`docs/18-testnet-launch-package.md`):
      runbook seed/validator/faucet/BlackScan + port/firewall + daftar
      prasyarat publik P1–P7 yang BELUM ADA (server, domain, pengumuman).
- [x] Skema insentif validator — DIPUTUSKAN pemilik Sesi 7 (`docs/06-validator-params.md` §5):
      testnet subsidi 10 tBKC/blok, 3 bulan, pagu 20 jt tBKC dari bucket reward
      validator; mainnet fee + 50% fee protokol BlackSwap, inflasi tetap 0%
- [ ] Validator onboarding
- [ ] Faucet (implementasi)
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
