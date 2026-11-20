# BLACKCHAIN — Roadmap (Testnet 3 Bulan)

**Status 21 Nov 2026, 02:15 WIB (Sesi 9 selesai, Sesi 12–13 sudah berjalan paralel):** Month 1 SELESAI dan terbukti. EVM live via
Jalur A (chain ID 20261120, denom abkc), repo sudah live di GitHub, website
live gratis di GitHub Pages. Sesi 8: rehearsal 4 validator terbukti.
**Sesi 9 SELESAI:** implementasi kode Fase 1 (ingest paralel) + pengukuran
E1/E2 (`docs/19`) — transfers 61,2 → 87,3 TPS, contract tetap ~49 TPS,
fork di devnet terpisah (belum di-merge). Sesi 10: **paket testnet publik TERBUKA** (`testnet/`
+ draft pengumuman `docs/20`) — tetapi jaringan live masih LOKAL
(127.0.0.1); belum ada endpoint publik. Sesi 11: paket deploy VPS SIAP
(script + runbook + `docs/21`); IP VPS diterima (103.147.8.20) tetapi
SSH gagal (port 22/80/443 tidak menjawab) — deploy tertahan. Sesi 12:
**faucet + BlackScan Lite + monitoring/insiden SELESAI dan JALAN**
melawan rehearsal lokal; rehearsal 4 validator height 923 (hash sama),
devnet height 11.359. Testnet yang bisa diakses internet masih menunggu
akses VPS + deploy seed + domain.

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

- [x] Public testnet — PAKET PUBLIK TERBUKA Sesi 10 (`testnet/`: genesis
      final + README cara bergabung + `seeds.md` jujur; draft pengumuman
      `docs/20` ID+EN, belum diposting). Chain ID 20261120 SUDAH
      dialokasikan setelah cek registry — bukan 9000/9001. Jaringan
      rehearsal 4 validator live height 923 (Sesi 12, hash sama di 4 node).
      Sesi 11: paket deploy VPS SIAP; IP VPS 103.147.8.20 diterima tetapi
      SSH gagal (port 22/80/443 tidak menjawab) — deploy seed tertahan
      sampai pemilik memeriksa status + firewall VPS. Yang MASIH kurang
      agar benar-benar bisa diakses internet: akses VPS + deploy seed,
      domain (P1/P2), tanggal buka + persetujuan pengumuman (lihat `docs/18` §7).
- [x] Parameter validator final — SELESAI Sesi 4 + Sesi 7: active-set maks 100, self-stake 1.000 BKC, slash double-sign 5% / downtime 1%, insentif hibrida (subsidi testnet 10 tBKC/blok, pagu 20 jt tBKC; mainnet fee + 50% fee protokol BlackSwap)
- [x] Benchmark TPS terukur — SELESAI Sesi 4 (maks ~89 TPS sustained, 0 tx gagal;
      bottleneck ingest ~110 tx/detik + blok ~1 detik + eksekusi serial;
      100.000 TPS tetap TARGET, jarak ~1.100×; laporan `docs/09-benchmark-tps.md`)
- [x] Jalur ke 100.000 TPS — RISET & DESAIN SELESAI Sesi 6 (`docs/10-tps-architecture-path.md`):
      rekomendasi ingest paralel + hardware dulu, lalu eksekusi paralel Block-STM;
      urutan Fase 1→4 DISETUJUI pemilik Sesi 7
      dan desain implementasi Fase 1 selesai (`docs/16-phase1-ingest-design.md`);
      **IMPLEMENTASI KODE FASE 1 SELESAI + TERUKUR Sesi 9** (`docs/19-phase1-implementation.md`,
      fork `build/blackchain-phase1/` + `build/evm-fork-phase1/`,
      endpoint `eth_sendRawTransactionBatch` live di devnet fork chain 20261120):
      transfers 61,2 → **87,3 TPS (+43%)**, submit 95 → 204 tx/dtk
      (1.301 tx/dtk mentah), contract sustained TETAP ~49 TPS (bottleneck
      blok ~5 dtk + eksekusi serial, bukan ingest). Plafon terukur tahap 1
      di VM ini: ~87 TPS transfer / ~49 TPS contract — estimasi lama
      300–1.000 TPS diganti angka terukur. Yang belum: merge fork ke pohon
      Jalur A (keputusan pemilik), Fase 1b (shard txpool internal),
      Fase 2–4, E1/E2 di hardware layak (blokir B).
- [x] Kontrak vesting/claim (Solidity + unit test) — SELESAI Sesi 4–5
      (OpenZeppelin v5.7.0, `forge test` 37/37 lolos); rencana deploy Sepolia
      SELESAI Sesi 7 (`docs/15-vesting-deployment-plan.md`): owner = multisig
      3-of-5 + timelock 48 jam DIPUTUSKAN; deploy menunggu alamat beneficiary/
      multisig + timestamp `start` (PLACEHOLDER, wajib diisi pemilik)
- [x] Spesifikasi BlackScan v0.1 — SELESAI Sesi 6 (`docs/11-blackscan-spec.md`;
      Blockscout, API /api/v2) + **IMPLEMENTASI BlackScan Lite SELESAI Sesi 12**
      (`repo/blackscan/`, `docs/23`): indexer SQLite + UI + API /api/v2,
      913 blok ter-index, lag 0 — BUKAN Blockscout penuh (keputusan pemilik)
- [x] Spesifikasi BlackSwap v0.1 — SELESAI Sesi 6 (`docs/12-blackswap-spec.md`;
      AMM x·y=k, fee 0,30%; kontrak, test & audit BELUM)
- [x] Spesifikasi faucet + panduan onboarding validator — SELESAI Sesi 6
      (`docs/13-faucet-validator-onboarding.md`) + **IMPLEMENTASI faucet
      SELESAI Sesi 12** (`repo/faucet/`, `docs/22`): 100 tBKC/klaim,
      PoW ringan, cooldown 24 jam; uji end-to-end LOLOS (tx `0x8dfe2e3c…`,
      blok 829, +100 tBKC); kapasitas efektif ~99 klaim (pool 10 jt tBKC
      di genesis berstatus STAKED — isi ulang butuh keputusan pemilik)
- [x] Checklist kesiapan testnet v0.1 — SELESAI Sesi 6, direvisi Sesi 7–12 (`docs/14-testnet-readiness.md`):
      rehearsal 4 validator TERBUKTI jalan (height 923, Sesi 12); 18 siap /
      6 sebagian / 5 belum / 0 diblokir komunikasi (draft pengumuman sudah
      ada, menunggu persetujuan); 4 hal konkret tersisa: alamat vesting,
      anggaran hardware/server+domain, keputusan genesis final + tanggal
      buka, persetujuan pengumuman
- [x] Monitoring + rencana insiden (P6) — SELESAI Sesi 12
      (`repo/monitoring/health-check.py` + `docs/24-monitoring-incident.md`):
      cek height/hash/fork/halt/faucet/BlackScan tiap run, tulis
      `data/status.json`, exit 0/1/2; uji 2x LOLOS (OK, 0 masalah).
      Cron tiap menit + alerting keluar BELUM dipasang (keputusan pemilik)
- [x] Paket deploy VPS seed — SIAP Sesi 11 (`repo/testnet/vps-deploy.sh` +
      `vps-runbook.md` + `docs/21`): hanya port P2P 26656 publik;
      eksekusi tertahan karena SSH ke 103.147.8.20 gagal (port tidak menjawab)
- [x] Perbaikan `.gitignore` — SELESAI Sesi 12: pola `seed*` yang terlalu
      lebar dipersempit ke `seed-phrase*`/`seedphrase*`/`*seed-phrase*`
      sehingga `testnet/seeds.md` tidak lagi tertangkap; `mnemonic*` tetap
      diabaikan (terverifikasi `git check-ignore`)
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
- [x] Faucet (implementasi) — SELESAI Sesi 12 (lokal, 127.0.0.1:8080)
- [x] BlackScan (explorer) live di testnet — SELESAI Sesi 12 sebagai
      BlackScan Lite (lokal, 127.0.0.1:8081); Blockscout penuh belum diputuskan
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
