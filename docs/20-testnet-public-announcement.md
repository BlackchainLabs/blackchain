# BLACKCHAIN — Draft Pengumuman Pembukaan Testnet Publik (Sesi 10, 2026-11-20)

**Status: DRAFT — BELUM DIPOSTING KE MANA PUN.**
**Pengumuman ini HANYA BOLEH dipublikasikan setelah persetujuan eksplisit
pemilik (Teuku).** Aturan misi: pengumuman resmi wajib persetujuan pemilik.
Jangan salin teks ini ke X/Telegram/Discord/GitHub/web sebelum pemilik
menyetujuinya — termasuk setelah VPS tersedia, karena tanggal buka dan
alamat seed publik di bawah masih kosong dan harus diisi dulu.

---

## Versi Bahasa Indonesia

**BLACKCHAIN Testnet Dibuka — Paket Publik Tersedia**

Hari ini kami membuka testnet BLACKCHAIN — Layer 1 hybrid yang kompatibel
EVM, dengan koin native BKC.

**Yang sudah terbukti berjalan:**
- Jaringan 4 validator yang sinkron penuh, transfer EVM terkonfirmasi di
  semua node, dan liveness teruji (jaringan tetap membuat blok saat satu
  validator mati).
- Chain ID EVM 20261120, denom abkc, genesis testnet tervalidasi.
- Throughput terukur ~89 TPS di devnet 1 validator — angka jujur dari
  pengukuran, bukan klaim. Target jangka panjang kami tetap 100.000 TPS,
  dan jalannya sudah dipetakan tahap demi tahap.

**Yang bisa kamu lakukan sekarang:**
- Unduh paket testnet (genesis, panduan bergabung, daftar seed) di
  https://github.com/BlackchainLabs/blackchain/tree/main/testnet
- Bangun node dari source dan pelajari chain-nya.
- Baca semua bukti dan dokumennya — semuanya terbuka di repo yang sama.

**Yang perlu kamu tahu dengan jujur:**
- Endpoint publik dan faucet belum live — jaringan yang berjalan saat ini
  masih di lingkungan lokal kami, dan seed publik menyusul setelah
  infrastruktur publik (server + IP publik) siap. Tanggal buka dan alamat
  seed akan diumumkan di kanal resmi ini.
- Token testnet (tBKC) tidak memiliki nilai. Tidak ada penjualan token,
  tidak ada janji imbal hasil.

Testnet ini adalah langkah pertama, bukan garis finis. Kami membangun
dengan bukti, bukan janji — dan kami mengundangmu untuk memeriksa
buktinya sendiri.

— Tim BLACKCHAIN
[LINK PENGUMUMAN / KANAL RESMI — DIISI PEMILIK]

---

## English version

**BLACKCHAIN Testnet Opens — Public Package Available**

Today we are opening the BLACKCHAIN testnet — an EVM-compatible hybrid
Layer 1 with the native coin BKC.

**What is already proven running:**
- A 4-validator network in full sync, EVM transfers confirmed on all
  nodes, and liveness tested (the network kept producing blocks with
  one validator down).
- EVM chain ID 20261120, denom abkc, validated testnet genesis.
- Measured throughput of ~89 TPS on a 1-validator devnet — an honest
  measured number, not a claim. Our long-term target remains 100,000 TPS,
  with the path mapped out stage by stage.

**What you can do now:**
- Download the testnet package (genesis, join guide, seed list) at
  https://github.com/BlackchainLabs/blackchain/tree/main/testnet
- Build a node from source and explore the chain.
- Read all the evidence and documentation — everything is open in the
  same repository.

**What you should know, honestly:**
- Public endpoints and the faucet are not live yet — the network running
  today is still in our local environment, and public seeds will follow
  once public infrastructure (server + public IP) is ready. The opening
  date and seed addresses will be announced on this official channel.
- Testnet tokens (tBKC) have no value. There is no token sale and no
  promise of returns.

This testnet is a first step, not a finish line. We build with evidence,
not promises — and we invite you to verify the evidence yourself.

— The BLACKCHAIN Team
[ANNOUNCEMENT LINK / OFFICIAL CHANNEL — TO BE FILLED BY OWNER]

---

## Checklist sebelum pengumuman ini boleh diposting

- [ ] VPS + IP publik tersedia dan seed node + node RPC berjalan di sana (P1)
- [ ] Alamat seed publik + RPC publik diisi di `testnet/seeds.md` dan diumumkan di teks di atas
- [ ] Tanggal buka testnet ditetapkan pemilik
- [ ] Faucet live (atau teks di atas diubah: "faucet menyusul")
- [ ] Pemilik menyetujui teks final + kanal posting (X / Telegram / Discord / GitHub Discussions / website)
- [ ] Pool subsidi (20 jt tBKC) + faucet (10 jt tBKC) sudah dipindah dari alamat operator ke community pool/multisig
