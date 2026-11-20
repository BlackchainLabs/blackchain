# BLACKCHAIN — Faucet Testnet & Panduan Onboarding Validator v0.1 (Sesi 6, 2026-11-20)

**Status:** SPESIFIKASI + PANDUAN — belum ada kode faucet, belum ada
testnet publik. Semua jumlah di bawah adalah USULAN; perubahan butuh
persetujuan pemilik.

## BAGIAN A — Faucet Testnet

### A.1 Tujuan

Memberi token testnet (tBKC, tanpa nilai) agar siapa pun bisa mencoba
chain, deploy kontrak, dan menyediakan likuiditas BlackSwap — tanpa
meminta seed phrase / private key siapa pun, dan tanpa membiarkan satu
pihak menguras faucet.

### A.2 Aturan klaim (usulan)

| Parameter | Nilai usulan | Alasan |
|---|---|---|
| Jumlah per klaim | **100 tBKC** per alamat per 24 jam | Cukup untuk puluhan ribu tx (gas testnet ~0) + deploy kontrak; tidak cukup untuk menguras faucet bila disalahgunakan |
| Cooldown | 24 jam per alamat DAN per IP | Mencegah klaim berulang |
| Batas harian global | **1.000.000 tBKC/hari** (10.000 klaim) | Bila tercapai, faucet berhenti sampai hari berikutnya + peringatan di UI; lindungi saldo faucet |
| Saldo faucet | Diisi dari alokasi komunitas testnet (jumlah BUTUH keputusan pemilik — lihat A.6) | Faucet adalah kontrak/alamat yang dananya transparan di BlackScan |
| Token lain | tUSDC mock: 1.000 tUSDC per klaim (untuk BlackSwap) | Dipisah dari tBKC agar likuiditas swap bisa dicoba |

### A.3 Anti-Sybil dasar (lapis, bukan jaminan)

Tidak ada anti-Sybil yang sempurna di testnet tanpa identitas. Yang
dipakai adalah lapis pertahanan yang menaikkan biaya serangan:

1. **CAPTCHA** (hCaptcha/Cloudflare Turnstile) di UI web — wajib.
2. **Rate limit per IP** — maks 5 klaim/hari/IP (di atas cooldown
   alamat).
3. **Cooldown alamat 24 jam** (§A.2).
4. **Batas harian global** (§A.2) — pemutus arus.
5. **Verifikasi opsional (tier 2):** klaim 1.000 tBKC bila alamat
   terhubung ke akun GitHub/X yang berumur >30 hari (opsional, bila
   diputuskan — menambah kompleksitas; default: TIDAK aktif).
6. **Daftar blokir:** alamat yang terdeteksi bot (pola klaim
   otomatis) dapat diblokir manual oleh operator faucet; daftar
   blokir dipublikasikan agar transparan.
7. **Tidak pernah meminta:** seed phrase, private key, atau tanda
   tangan atas pesan yang tidak jelas. Faucet HANYA meminta alamat
   (0x...) — siapa pun yang meminta seed phrase atas nama faucet
   adalah penipuan.

### A.4 Arsitektur (rencana)

```
Pengguna → Web UI faucet → CAPTCHA verify → API faucet (rate limit)
        → antrean klaim → wallet operator (hot wallet KHUSUS faucet,
          saldo terbatas, BUKAN treasury) → transfer tBKC → BlackScan
```

- Hot wallet faucet dipisah dari treasury; saldo hot wallet dibatasi
  (mis. 7 hari kebutuhan) dan diisi ulang manual oleh operator.
- API mencatat setiap klaim (alamat, IP hash, waktu, jumlah) di
  database; log dapat diaudit.
- Bila API mati, UI menampilkan status "faucet offline" — tidak ada
  klaim yang hilang diam-diam.

### A.5 Endpoint (rencana)

| Endpoint | Fungsi |
|---|---|
| `POST /api/claim` | Body: `{address, captcha_token}` → antrekan klaim; balas `{tx_hash, amount}` atau error (cooldown / limit / captcha gagal) |
| `GET /api/status` | Saldo faucet, sisa kuota harian, status layanan |
| `GET /api/claims/:address` | Riwayat klaim alamat (kapan boleh klaim lagi) |

### A.6 Hal terbuka (faucet — butuh keputusan pemilik)

1. Total alokasi tBKC untuk faucet testnet (dari porsi komunitas 950 jt).
2. Apakah tier verifikasi GitHub/X (A.3 butir 5) diaktifkan.
3. Siapa operator faucet + siapa yang memegang hot wallet.

## BAGIAN B — Panduan Onboarding Validator

### B.1 Siapa yang bisa jadi validator testnet

Siapa pun yang memenuhi hardware minimum (§B.2), menjalankan node
dengan benar, dan menyetor self-stake minimum **1.000 BKC** (aturan
operasional, lihat `docs/06-validator-params.md`). Tidak ada proses
seleksi tertutup di testnet — tetapi operator yang melanggar aturan
(termasuk double-sign) akan di-slash sesuai parameter yang berlaku.

### B.2 Hardware minimum (testnet — usulan, mengikuti `docs/10` §4)

| Komponen | Minimum testnet | Direkomendasikan |
|---|---|---|
| CPU | 8 vCPU modern (≥3 GHz) | 16 vCPU |
| RAM | 32 GB | 64 GB |
| Disk | 500 GB NVMe SSD | 2 TB NVMe SSD |
| Jaringan | 100 Mbps, IP publik statis, port 26656/26657 terbuka | 1 Gbps |
| OS | Ubuntu 22.04/24.04 LTS (atau Debian 12) | sama |
| Uptime | target ≥99% (downtime melewati window 100 blok → jail + slash 1%) | monitoring 24/7 |

**Catatan:** hardware di atas adalah untuk testnet. Angka ini
berdasarkan kebutuhan Cosmos SDK + EVM; validasi nyata = jalankan node
dan ukur (CPU/RAM/disk saat sinkronisasi + saat beban).

### B.3 Langkah setup (ringkas — detail perintah di `VALIDATOR_GUIDE.md`)

1. **Siapkan server** (§B.2) + buat user non-root + firewall
   (hanya port yang dibutuhkan).
2. **Instal binary** `blackchaind` (rilis testnet — tautan + checksum
   SHA-256 dipublikasikan; JANGAN jalankan binary tanpa verifikasi
   checksum).
3. **Inisialisasi:** `blackchaind init <nama-moniker> --chain-id
   blackchain_20261120-1` (chain ID testnet final dikonfirmasi saat
   pengumuman testnet — DEVNET saat ini memakai chain ID yang sama,
   tetapi genesis testnet publik BERBEDA).
4. **Buat / pulihkan kunci validator** (`blackchaind keys add
   <nama>`). **SIMPAN MNEMONIC DI TEMPAT AMAN, OFFLINE, TIDAK PERNAH
   DIBAGIKAN.** Kehilangan kunci validator = kehilangan validator.
5. **Dapatkan tBKC dari faucet** (§A) untuk biaya transaksi
   `create-validator`.
6. **Unduh genesis testnet** (URL resmi) + verifikasi checksum-nya;
   letakkan di `~/.blackchain/config/genesis.json`.
7. **Atur peers:** `persistent_peers` di `config.toml` (daftar seed
   resmi dipublikasikan saat testnet dibuka).
8. **Mulai node & sinkronisasi:** `blackchaind start`; pantau
   `catching_up` sampai `false` (cek via `curl localhost:26657/status`).
9. **Buat validator:** `blackchaind tx staking create-validator`
   dengan self-stake 1.000 BKC, komisi (min 5%), deskripsi & website
   (opsional). **Periksa kembali semua nilai sebelum kirim** —
   komisi minimum tidak bisa diturunkan setelahnya.
10. **Verifikasi:** alamat validator muncul di BlackScan (halaman
    validator) + `blackchaind query staking validator <alamat>`.
11. **Operasional:** aktifkan monitoring (lihat §B.4), siapkan
    sentry node bila memungkinkan, dan JANGAN menjalankan validator
    dan RPC publik di node yang sama tanpa isolasi.

### B.4 Monitoring & operasional (wajib)

- **Metrik yang dipantau:** height terbaru, `catching_up`, jumlah
  peer, missed blocks (tanda akan kena slash downtime), penggunaan
  CPU/RAM/disk, saldo akun operator.
- **Alert:** node berhenti >5 menit; missed blocks berturut-turut;
  disk <20% tersisa; upgrade chain dijadwalkan.
- **Backup:** backup `priv_validator_key.json` secara terenkripsi &
  offline (JANGAN pernah menjalankan DUA node dengan kunci validator
  yang sama — itu double-sign → slash 5%).
- **Upgrade:** ikuti pengumuman resmi; uji upgrade di devnet dulu
  bila memungkinkan; jangan upgrade di tengah epoch voting.

### B.5 Cara join devnet saat ini (SEBELUM testnet publik)

Devnet lokal identitas BKC (`blackchain_20261120-1`, EVM chain ID
20261120, JSON-RPC 127.0.0.1:8555) saat ini berjalan di 1 validator
lokal dan **belum membuka peer publik** — belum ada seed/peer resmi
yang dipublikasikan. Validator eksternal BELUM bisa join devnet ini.
Pengumuman peer + genesis testnet publik akan menyusul setelah
keputusan pemilik di `docs/14` selesai. Jangan percaya daftar peer
dari sumber tidak resmi.

### B.6 Hal terbuka (validator — butuh keputusan pemilik)

1. Kriteria penerimaan validator testnet (apakah terbuka penuh atau
   ada daftar izin awal).
2. Skema insentif validator (lihat `docs/14` blokir #1) — tanpa ini,
   validator hanya bermodal fee yang kecil di testnet.
3. Besaran self-stake final untuk testnet (usulan 1.000 BKC).
4. Apakah downtime slash dilonggarkan sementara di awal testnet
   (usulan 0,1% — lihat `docs/06`).
