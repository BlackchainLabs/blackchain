# BLACKCHAIN — Rencana Deploy Vesting & Klaim ke Sepolia (Sesi 7, 2026-11-20)

**Status:** RENCANA DEPLOY — dokumen ini adalah checklist dan urutan
langkah, BUKAN eksekusi. Tidak ada kontrak yang di-deploy di sesi ini.
Semua alamat di bawah adalah PLACEHOLDER dan **WAJIB DIISI PEMILIK
SEBELUM DEPLOY**. Jangan pernah mengisi alamat hasil karangan.

**Keputusan pemilik Sesi 7 (disampaikan lewat Muse utama):** owner kontrak
= **multisig + timelock** (bukan EOA tunggal). Kontrak: BKC ERC-20 +
TeamVesting + CommunityClaim, OpenZeppelin v5.7.0, `forge test` 37/37
lolos (Sesi 5). Spec kontrak: `docs/07-vesting-contracts.md`.

## 1. Keputusan kepemilikan — DIPUTUSKAN

| Komponen | Keputusan | Alasan |
|---|---|---|
| Multisig | **Gnosis Safe, threshold 3-of-5** | 3-of-5 menahan kehilangan/kompromi 2 kunci sekaligus, dan tetap bisa bertindak bila 2 penandatangan tidak tersedia. 2-of-3 terlalu rapuh (1 kunci hilang + 1 kompromi = dana terkunci/dicuri); 4-of-7 dan seterusnya memperlambat respons darurat (mis. pause saat insiden) |
| Anggota multisig | **PLACEHOLDER — 5 alamat EOA pemilik/operator tepercaya** (`0x...` × 5) | WAJIB DIISI PEMILIK. Syarat: tiap alamat adalah hardware wallet / kunci terpisah milik orang berbeda; tidak ada dua alamat yang dipegang orang yang sama |
| Timelock | **OpenZeppelin TimelockController, delay 48 jam** | 48 jam cukup untuk komunitas/validator memperhatikan dan bereaksi terhadap proposal berbahaya (mis. perubahan owner), tapi tidak melumpuhkan respons darurat — karena `pause()` di CommunityClaim TIDAK melewati timelock bila dipegang multisig secara langsung (lihat §4) |
| Proposer timelock | Multisig (Safe) | Hanya Safe yang boleh mengajukan aksi timelock |
| Executor timelock | Multisig (Safe) | Hanya Safe yang boleh mengeksekusi; executor terbuka (siapa pun) DITOLAK untuk menghindari eksekusi paksa oleh pihak luar |
| Canceller timelock | Multisig (Safe) | Safe dapat membatalkan proposal yang salah sebelum dieksekusi |
| Owner TeamVesting | **Timelock** (alamat timelock, diisi di constructor `owner_`) | Semua aksi owner (revoke, transferOwnership) melewati delay 48 jam |
| Owner CommunityClaim | **Timelock** (alamat timelock, diisi di constructor `owner_`) | `setMerkleRoot` dan `recoverRemaining` melewati delay 48 jam |
| Initial holder BKC | **Multisig (Safe)** — menerima seluruh 1 miliar BKC di constructor | Safe sebagai treasury mendanai kontrak vesting/klaim; timelock tidak memegang dana, hanya otoritas |
| `renounceOwnership` | **DILARANG** selama vesting/klaim aktif | Melepas owner = kontrak tidak bisa di-revoke/diperbaiki lagi; sudah diperingatkan di `docs/07` §7 butir 10 |

## 2. Parameter yang masih PLACEHOLDER (wajib diisi pemilik)

| Parameter | Format | Catatan |
|---|---|---|
| 5 alamat anggota multisig | `0x...` (5 alamat, checksum) | Hardware wallet, orang berbeda |
| Alamat beneficiary tim | `0x...` | Penerima 50 jt BKC dari TeamVesting; sebaiknya alamat Safe tim atau timelock kedua — BUKAN EOA pribadi |
| Timestamp `start` vesting | Unix timestamp, mis. `1790000000` | Disarankan = tanggal mainnet (bukan tanggal deploy Sepolia); di Sepolia pakai tanggal uji yang disepakati |
| Total alokasi TeamVesting | 50.000.000 BKC (50 jt × 10^18) | Tetap; cliff 90 hari + linear 270 hari, penuh 360 hari |
| Merkle root CommunityClaim | `bytes32 0x...` | Dihasilkan dari daftar klaim komunitas + skrip `scripts/merkle-claims.py` (belum dibuat); daftar alamat + jumlah = PLACEHOLDER |
| Pool klaim komunitas | Jumlah BKC + daftar alamat | Anti-Sybil: daftar berasal dari partisipan testnet terverifikasi (uptime validator, kontributor) — kriteria di `docs/04` §5; skor anti-Sybil belum dirancang (pekerjaan Month 2) |

## 3. Urutan deploy (checklist — jalankan hanya setelah §2 terisi)

Urutan ini penting karena kontrak vesting/klaim menerima alamat
timelock di constructor — timelock HARUS sudah ada sebelum keduanya
di-deploy. BKC menerima `initialHolder` di constructor.

1. **Siapkan akun deployer** — EOA sekali pakai dengan ETH Sepolia
   secukupnya (gas saja). Deployer BUKAN owner jangka panjang apa pun.
2. **Deploy Gnosis Safe 3-of-5** — catat alamat Safe + tx hash;
   verifikasi threshold dan daftar owner di Etherscan Sepolia.
3. **Deploy TimelockController** (delay 48 jam, proposer = Safe,
   executor = Safe, admin = Safe) — catat alamat timelock.
4. **Deploy BKC** (`initialHolder` = alamat Safe) — 1 miliar BKC masuk
   ke Safe. Verifikasi supply di Etherscan.
5. **Deploy TeamVesting** (`token_` = BKC, `beneficiary_` = PLACEHOLDER
   §2, `owner_` = alamat timelock, `start_` = PLACEHOLDER §2,
   `totalAllocation_` = 50 jt BKC).
6. **Deploy CommunityClaim** (`token_` = BKC, `owner_` = alamat
   timelock, `merkleRoot_` = PLACEHOLDER §2).
7. **Danai kontrak dari Safe** — transfer 50 jt BKC ke TeamVesting;
   transfer pool klaim ke CommunityClaim. Semua transfer dilakukan
   lewat transaksi Safe (3 tanda tangan), BUKAN dari deployer.
8. **Verifikasi source code** semua kontrak di Etherscan Sepolia
   (flatten atau via Foundry `forge verify-contract`).
9. **Uji alur di Sepolia** — claim Merkle dengan alamat uji, release
   vesting setelah warp waktu (atau tunggu cliff uji), pause/unpause,
   revoke sebelum cliff pada kontrak uji kedua. Catat semua tx hash.
10. **Serah terima owner** — pastikan `owner()` TeamVesting dan
    CommunityClaim = alamat timelock (bukan deployer, bukan Safe
    langsung). Bila ada yang salah, perbaiki SEBELUM mengumumkan.

## 4. Tanggap darurat — siapa bisa apa

| Aksi | Siapa | Lewat timelock? |
|---|---|---|
| `pause()` / `unpause()` CommunityClaim | Timelock (setelah 48 jam) — ATAU multisig langsung bila dalam keadaan darurat kontrak uji | Rekomendasi: di Sepolia, `pause()` tetap lewat timelock; untuk mainnet, pertimbangkan peran `PAUSER` terpisah di tangan multisig agar insiden bisa dihentikan dalam hitungan menit, bukan 48 jam. Keputusan ini diambil sebelum deploy mainnet, bukan di sesi ini |
| `revoke()` TeamVesting (sebelum cliff) | Timelock, setelah 48 jam | Ya — revoke adalah aksi berat dan memang harus lambat |
| `setMerkleRoot` | Timelock, setelah 48 jam | Ya |
| `recoverRemaining` | Timelock, setelah 48 jam | Ya |
| Transfer dana dari Safe | 3-of-5 tanda tangan | Tidak (Safe bukan timelock) |

## 5. Pemetaan abkc ↔ BKC ERC-20 — status: BELUM diputuskan teknisnya

Fakta: koin native chain BLACKCHAIN adalah `abkc` di modul bank Cosmos;
BKC ERC-20 adalah representasi EVM untuk vesting/klaim. Keduanya belum
terhubung secara teknis. Opsi yang dipertimbangkan:

| Opsi | Cara kerja | Kelebihan | Kekurangan | Rekomendasi |
|---|---|---|---|---|
| (a) Modul mint-burn kanonik | x/evm + bank: lock `abkc` → mint BKC ERC-20; burn BKC → unlock `abkc` | Satu supply, tidak ada wrapped token kedua | Butuh kode custom di fork Cosmos EVM + audit berat | Target jangka panjang mainnet |
| (b) Wrapped token wBKC | Kontrak lock `abkc` (via precompile) → mint wBKC ERC-20; sebaliknya burn → unlock | Lebih sederhana; pola umum di Cosmos EVM | Dua representasi beredar (BKC vs wBKC) membingungkan; butuh precompile lock yang aman | Alternatif bila (a) terlalu berat |
| (c) TIDAK ada pemetaan saat Sepolia | BKC ERC-20 Sepolia murni untuk menguji vesting/klaim; `abkc` devnet tetap terpisah | Tidak ada risiko teknis; pengujian vesting tetap valid | Distribusi mainnet butuh jembatan nyata — tidak boleh diklaim selesai | **DIPILIH untuk fase Sepolia** |

**Rekomendasi Sesi 7:** pakai opsi (c) untuk deploy Sepolia; desain
opsi (a) sebagai pekerjaan Month 2–3 dengan audit terpisah. Jangan
pernah mengklaim distribusi BKC mainnet selesai sebelum pemetaan ini
dibangun dan diaudit.

## 6. Jadwal audit & deploy

| Tahap | Syarat masuk | Keterangan |
|---|---|---|
| Audit internal (Muse) | Kontrak final + test 37/37 | Sudah lolos Sesi 5; ulangi setelah perubahan apa pun |
| Deploy Sepolia | §2 terisi + §3 langkah 1–10 | Uji fungsional; token Sepolia tanpa nilai |
| Audit eksternal independen | Setelah uji Sepolia bersih | WAJIB sebelum mainnet; auditor belum dipilih — pekerjaan Month 3 |
| Deploy mainnet | Audit eksternal lolos + pemetaan abkc↔BKC selesai + persetujuan eksplisit pemilik | Bukan di sesi ini; bukan dalam waktu dekat |

## 7. Yang TIDAK dilakukan dokumen ini

- Tidak mengisi alamat apa pun (semua placeholder).
- Tidak mengeksekusi deploy, transfer, atau transaksi apa pun.
- Tidak menjanjikan tanggal mainnet atau nilai token.
