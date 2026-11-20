# BLACKCHAIN — Deploy Seed Node Publik di VPS (Sesi 11, 2026-11-21)

**Status:** DESAIN + PAKET DEPLOY SIAP, BELUM DIEKSEKUSI. Pemilik (Teuku)
menyatakan sudah menggunakan VPS pada 2026-11-21 00:01 WIB, tetapi IP
publik, username SSH, OS/distro, dan konfirmasi kunci SSH belum
diterima — karena itu belum ada SSH ke VPS mana pun dan belum ada
deploy. Paket: `repo/testnet/vps-deploy.sh` + `repo/testnet/vps-runbook.md`
(ditulis Sesi 11, sintaks teruji: `bash -n` lolos, `--dry-run` lolos,
logika edit config teruji pada salinan `config.toml`/`app.toml` val1).

Dokumen terkait: runbook peluncuran `docs/18`, rehearsal `docs/17`,
checklist `docs/14`, pengumuman draft `docs/20`.

## 1. Masalah yang dipecahkan

Sejak Sesi 8–10, testnet BLACKCHAIN hanya hidup di satu VM lokal:
4 validator di 127.0.0.1, tanpa IP publik, tanpa seed yang bisa di-dial
dari internet. VM ini hanya bisa egress — tidak ada inbound port yang
bisa dibuka dari dalamnya. Satu-satunya jalan ke publik adalah server
di luar VM ini: VPS milik pemilik (prasyarat P1, `docs/18` §7).

## 2. Arsitektur yang dipilih

```
Internet
   │  P2P 26656/TCP (satu-satunya port publik)
   ▼
┌─────────────────────────────┐
│ VPS — blackchain-seed-1     │  seed node + full node publik
│ ~/.blackchain               │  BUKAN validator (tanpa kunci
│ blackchaind-seed.service    │  validator, tanpa self-stake)
└──────────────┬──────────────┘
               │  dial KELUAR (outbound) dari VM lokal
               │  validator lokal TIDAK BISA di-dial dari luar
   ┌───────────┴───────────┐
   ▼                       ▼
VM lokal: 4 validator rehearsal (127.0.0.1:26776–26806)
+ devnet BKC 1-validator (terpisah, tidak tersentuh)
+ node fork Phase 1 Sesi 9 (terpisah, tidak tersentuh)
```

### 2.1 Seed non-validator

VPS menjalankan node CometBFT biasa dengan `seed_mode = true`:
merespons peer exchange, menyimpan dan menyebarkan alamat peer, TIDAK
ikut voting konsensus. Tidak ada gentx untuk seed, tidak ada self-stake,
tidak ada kunci validator di VPS. `blackchaind init` memang membuat
`priv_validator_key.json` di home node — file itu INERT untuk seed
(bukan anggota validator set) dan JANGAN PERNAH dibagikan, disalin
keluar VPS, atau dipakai membuat validator.

Alasan seed, bukan validator ke-5 di VPS: (a) kunci validator rehearsal
dibuat di VM ini dengan keyring `test` — memindahkannya keluar VM
adalah risiko keamanan yang tidak perlu; (b) seed adalah komponen
paling kecil yang membuka jaringan ke publik — validator eksternal
nanti bergabung lewat seed ini (`docs/18` §2); (c) bila VPS bermasalah,
rantai lokal tetap jalan (rollback `vps-runbook.md` §6).

### 2.2 Arah koneksi: dial keluar dari lokal

Fakta jaringan yang menentukan desain ini:

- Node lokal listen HANYA di 127.0.0.1 (P2P 26776/26786/26796/26806).
  Alamat itu tidak bisa di-dial dari internet — 127.0.0.1 selalu berarti
  "mesin sendiri".
- VM ini BISA dial keluar ke IP publik (egress terbuka).
- Karena itu `persistent_peers` seed VPS dikosongkan, dan sebaliknya
  keempat validator lokal menambahkan seed sebagai persistent peer.
  Setelah seed hidup, validator eksternal bergabung lewat seed VPS —
  mereka tidak perlu (dan tidak bisa) menghubungi validator lokal
  secara langsung.

### 2.3 TANPA genesis baru — rantai tetap yang sama

Genesis yang dipakai seed adalah SALINAN PERSIS
`repo/testnet/blackchain-testnet-genesis.json` (chain-id
`blackchain_20261120-1`, 4 gentx @ 1.000 BKC, total supply genesis
30.080.000 BKC, sha256 `0fbd6b09…52431`). Seed melakukan sync dari
genesis hingga height saat ini (~500+), lalu mengikuti rantai yang
sudah berjalan. Height, saldo, dan transaksi rehearsal BERLANJUT —
tidak ada yang dibuang.

**Catatan jujur (bukan usulan perubahan):** `docs/18` §8 merekomendasikan
genesis BARU untuk testnet publik yang serius, karena kunci validator
rehearsal dibuat di VM ini dengan keyring `test`. Keputusan Sesi 11 —
atas instruksi pemilik "Jalankan" untuk VPS yang sudah ada — adalah
melanjutkan rantai yang sama, agar testnet bisa dibuka sekarang tanpa
mengulang rehearsal. Konsekuensinya dicatat di sini: kunci validator
tetap di VM ini; bila di kemudian hari pemilik menginginkan validator
genesis dengan kunci yang dibuat di server masing-masing, itu berarti
genesis baru + rantai baru (jalur `docs/18` §8 opsi B) dan menjadi
keputusan pemilik tersendiri — BUKAN bagian dari Sesi 11.

### 2.4 Binary ditransfer via scp, bukan dari GitHub

Scaffold chain TIDAK ADA di repo GitHub (`build/` di-gitignore, dan
kode scaffold memang tidak ikut ter-commit). Jadi tidak ada "build dari
source" yang bisa dijalankan di VPS dari repo. Binary Jalur A
(`build/blackchaind-sdk54-bkc`, SDK v0.54.5 + Cosmos EVM v0.7.4,
~199 MB, sha256 `37766ab8…b9f06`) ditransfer dari VM ini via scp,
lalu diverifikasi sha256-nya oleh `vps-deploy.sh` sebelum dipakai.
Validator eksternal yang bergabung nanti tetap mengikuti
`docs/18` §2 (build dari source bila repositori scaffold sudah
dipublikasikan, atau memakai binary rilis resmi bila sudah ada —
keduanya BELUM ADA saat dokumen ini ditulis).

## 3. Port & firewall (keputusan Sesi 11)

Sesuai `docs/18` §5, dengan satu penegasan: TIDAK ADA port baru yang
dibuka diam-diam.

| Port | Arah | Keputusan | Alasan |
|---|---|---|---|
| 26656/TCP P2P | Publik | **BUKA** | Satu-satunya port konsensus yang wajib publik; seed tidak berguna tanpanya |
| 26657/TCP RPC | Lokal saja | **TUTUP** (bind 127.0.0.1) | RPC CometBFT memberi status/kontrol node; tidak perlu di internet untuk seed |
| 8545/8546 JSON-RPC/WS | Lokal saja | **TUTUP** (bind 127.0.0.1) | Lihat §4 — RPC publik adalah keputusan pemilik terpisah |
| 9090/TCP gRPC | Lokal saja | **TUTUP** (bind 127.0.0.1) | Operator saja |
| 1317/TCP REST | — | **NONAKTIF** (`enable = false`) | Tidak dibutuhkan seed |
| 22/TCP SSH | Admin | **BUKA** | Akses admin; idealnya dibatasi ke IP admin (catatan di script) |

UFW di VPS: `allow 22, 26656`; `deny 26657, 8545, 8546, 9090, 1317`
(deny eksplisit sebagai pertahanan berlapis di atas default-deny).
`vps-deploy.sh` juga mencatat opsi membatasi SSH ke IP admin tertentu —
tidak diterapkan otomatis karena IP admin belum diketahui.

## 4. RPC publik read-only — DIPUTUSKAN: TIDAK DIBUKA di Sesi 11

**Keputusan:** JSON-RPC EVM (8545) dan RPC CometBFT (26657) di VPS
TETAP tertutup untuk internet pada Sesi 11. Keduanya di-enable tetapi
hanya di-bind ke 127.0.0.1, sehingga operator masih bisa query dari
dalam VPS (verifikasi `eth_chainId`, `status`, `net_info`).

**Justifikasi:**

- Seed node tidak membutuhkan RPC publik untuk menjalankan fungsinya
  (discovery peer + relay blok). Membuka RPC menambah permukaan serang
  tanpa manfaat untuk tujuan Sesi 11.
- Testnet masih dalam tahap pembukaan awal: belum ada faucet, belum ada
  BlackScan, belum ada monitoring (P5/P6). RPC publik baru berguna
  ketika ada pengguna luar yang benar-benar mengirim transaksi — dan
  itu membutuhkan faucet yang live terlebih dahulu.
- `docs/18` §5 sudah menetapkan pola yang sama (RPC tidak langsung,
  hanya via reverse proxy + rate limit).

**Bila pemilik nanti memutuskan membuka RPC publik** (keputusan
pemilik, bukan otomatis), syarat minimum yang harus dipenuhi dulu:

1. Reverse proxy (mis. nginx/Caddy) di depan 8545/26657, dengan TLS.
2. Rate limit (mis. nginx `limit_req`: ≤ 10 req/detik/IP untuk RPC
   umum; endpoint berat seperti `eth_getLogs` dibatasi/dinonaktifkan).
3. Hanya metode read-only yang diteruskan (`eth_chainId`,
   `eth_blockNumber`, `eth_getBalance`, `eth_call`, dsb.); metode
   tulis/admin (`personal_*`, `admin_*`, `debug_*`, `eth_sendRawTransaction`
   tanpa batas) TETAP tertutup atau lewat node RPC terpisah dengan
   API key.
4. UFW membuka 443 saja (bukan 8545/26657 langsung); port mentah
   tetap deny.
5. Monitoring + alert bila rate limit sering tersentuh (indikasi abuse).

Poin ini dicatat sebagai keputusan pemilik yang MASIH TERBUKA — bukan
sebagai pekerjaan Sesi 11.

## 5. Operasional

- **Service:** systemd `blackchaind-seed` (`Restart=always`,
  `RestartSec=10`, `LimitNOFILE=65535`), berjalan sebagai user
  non-root yang sama dengan pemilik deploy. Log: `journalctl -u
  blackchaind-seed -f`.
- **Restart validator lokal:** satu per satu, kuorum 3/4 dijaga
  (maksimal 1 node mati bersamaan). Perintah persis di
  `vps-runbook.md` §4 — JANGAN `pkill blackchaind` (pernah membunuh
  devnet lain, Sesi 2).
- **Rollback:** matikan seed VPS + kembalikan `persistent_peers` lokal
  ke nilai asli (tabel di runbook §4.1/§6). Rantai lokal tidak
  tergantung seed.
- **Monitoring/insiden:** BELUM ADA (P6 tetap terbuka). Sampai
  monitoring dibangun, kesehatan seed diperiksa manual:
  `systemctl status blackchaind-seed`, `curl localhost:26657/status`,
  `curl localhost:26657/net_info`.

## 6. Prasyarat P1–P7 — status setelah Sesi 11

(dari `docs/18` §7; "Sesi 11" = paket deploy ini, persiapan saja)

| # | Prasyarat | Status sebelum Sesi 11 | Status setelah Sesi 11 |
|---|---|---|---|
| P1 | Server + IP publik | BELUM ADA | 🔄 **SEBAGIAN** — VPS sudah disediakan pemilik (dinyatakan 2026-11-21 00:01 WIB); IP/akses belum diterima; deploy BELUM dieksekusi. P1 baru PENUH setelah seed terverifikasi live + bisa di-dial dari luar (runbook §5) |
| P2 | Domain + DNS | BELUM ADA | ⬜ Tetap belum ada (pemilik memilih jalur gratis; domain `blackchainlabs.io` terdaftar pihak lain — lihat website) |
| P3 | Genesis final + tanggal buka | DRAFT ADA | 🔄 Tetap draft — Sesi 11 memakai genesis ini apa adanya (rantai sama); keputusan final pakai-apa-adanya vs buat-ulang + pemindahan pool + tanggal buka masih menunggu pemilik |
| P4 | Pengumuman resmi | DRAFT (`docs/20`) | 🔄 Tetap draft — belum diposting; butuh persetujuan eksplisit + alamat seed publik terverifikasi |
| P5 | Faucet + BlackScan live | BELUM DIBANGUN | ⬜ Tetap belum dibangun (spec saja, `docs/11`/`docs/13`) |
| P6 | Monitoring, rencana insiden, state sync | BELUM DIBANGUN | ⬜ Tetap belum dibangun |
| P7 | Alamat vesting | PLACEHOLDER | ⬜ Tetap placeholder (`docs/15` §2); tidak menghalangi testnet chain |

**Kesimpulan jujur Sesi 11:** paket deploy VPS SIAP (script + runbook +
desain ini), tetapi TIDAK ADA endpoint publik yang live sampai eksekusi
§3–§5 runbook selesai dan terverifikasi. Setelah seed live, status
yang benar menjadi: "testnet bisa diakses internet lewat seed publik;
faucet/BlackScan/monitoring belum ada". Blokir konkret pemilik tetap 4:
(A) alamat vesting, (B) akses VPS — sebagian terpenuhi (VPS ada, akses
belum), (C) genesis final + tanggal buka, (D) persetujuan pengumuman.

## 7. Yang masih dibutuhkan sebelum eksekusi (ringkas)

1. IP publik VPS.
2. Username SSH (+ OS/distro).
3. Konfirmasi kunci publik `ssh-ed25519 AAAAC3...CIDf7Z hatch` sudah
   masuk `authorized_keys` VPS.
4. (Opsional) spesifikasi VPS (vCPU/RAM/disk) — menentukan apakah VPS
   ini juga layak jadi node RPC/archive nanti, atau hanya seed.

Daftar lengkap + format ada di `vps-runbook.md` §1.
