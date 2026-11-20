# BLACKCHAIN — Testnet Publik: Paket Bergabung

**Status 20 Nov 2026 (Sesi 10): PAKET PUBLIK TERBUKA — JARINGAN LIVE MASIH LOKAL.**

Baca ini dulu, jujur: file-file di folder ini (genesis, panduan, daftar seed)
sudah dipublikasikan di repo ini dan bisa dipakai siapa pun. Tetapi jaringan
testnet yang sedang berjalan saat ini **hanya hidup di satu VM lokal
(127.0.0.1)** — tidak ada endpoint publik yang bisa dijangkau internet.
Artinya: hari ini kamu BISA membaca paket ini, membangun binary dari source,
dan menjalankan node sendiri dengan genesis yang sama; kamu BELUM BISA
terhubung ke jaringan 4 validator yang sedang berjalan, karena tidak ada
seed node publik. Seed publik baru ada setelah VPS + IP publik tersedia
(lihat `docs/18-testnet-launch-package.md` §7, prasyarat P1/P2).

## Identitas chain

| Parameter | Nilai |
|---|---|
| CometBFT chain-id | `blackchain_20261120-1` |
| EVM chain ID | `20261120` (`0x1352900`) |
| Denom native | `abkc` (1 BKC = 10^18 abkc) |
| Framework | Cosmos SDK v0.54.5 + CometBFT + Cosmos EVM v0.7.4 |
| Genesis | `blackchain-testnet-genesis.json` (di folder ini) |
| Total supply genesis | 30.080.000 BKC (4 gentx @ 1.000 BKC self-stake; pool subsidi 20 jt + faucet 10 jt dipegang alamat operator selama rehearsal — wajib dipindah ke community pool/multisig sebelum pembukaan publik; TANPA alokasi tim/mainnet) |
| Block time | ~5 detik (devnet/rehearsal; diukur) |
| TPS terukur | ~89 TPS sustained di devnet 1 validator, VM 1,5 CPU (Sesi 4, `docs/09-benchmark-tps.md`). 100.000 TPS adalah TARGET, bukan hasil. |

## Isi folder ini

| File | Isi |
|---|---|
| `blackchain-testnet-genesis.json` | Genesis testnet final (draft) — `genesis validate` LOLOS. Chain-id `blackchain_20261120-1`, 4 gentx, total supply 30.080.000 BKC. |
| `README.md` | File ini — cara bergabung. |
| `seeds.md` | Daftar seed node — BACA PERINGATANNYA: hanya alamat 127.0.0.1 (VM lokal), bukan seed publik. |

Dokumen terkait (di `docs/`): `17-testnet-multivalidator.md` (bukti rehearsal
4 validator + status pembukaan publik), `18-testnet-launch-package.md`
(runbook seed/validator/faucet/BlackScan + prasyarat publik P1–P7),
`13-faucet-validator-onboarding.md` (spec faucet + panduan validator),
`20-testnet-public-announcement.md` (draft pengumuman — belum diposting).

## Cara bergabung (setelah seed publik tersedia)

Langkah-langkah ini mengikuti runbook `docs/18`. Sampai seed publik
diumumkan, langkah 4–6 BELUM bisa dilakukan terhadap jaringan live.

### 1. Persyaratan hardware minimum

- 8 vCPU / 32 GB RAM / 500 GB NVMe (lihat `docs/13` B.1)
- Go 1.23+ (untuk build dari source), Git, koneksi internet stabil
- Port yang dibuka: **26656 (P2P)** ke publik; RPC (26657), EVM JSON-RPC
  (8545), gRPC (9090), REST (1317) **TIDAK BOLEH** dibuka ke publik
  (lihat `docs/18` §5).

### 2. Bangun binary dari source

Belum ada rilis binary yang sudah dikompilasi. Bangun dari source repo
ini (pohon Jalur A, SDK v0.54.5 + Cosmos EVM v0.7.4):

```bash
git clone https://github.com/BlackchainLabs/blackchain.git
cd blackchain
# Ikuti instruksi build di DEVELOPER_GUIDE.md / docs/05-evm-integration.md
# Binary hasil build: blackchaind (atau blackchaind-sdk54-bkc pada
# pohon devnet Sesi 3–4 — lihat docs/05 untuk detail build)
```

> Catatan: pohon chain (Cosmos SDK scaffold) TIDAK ikut ter-commit di
> repo ini (di-`gitignore`, lihat `repo/.gitignore`); instruksi build
> lengkap ada di `docs/05-evm-integration.md`. Bila langkah build tidak
> cocok dengan repo saat ini, laporkan sebagai issue di GitHub.

### 3. Init node dengan genesis testnet

```bash
blackchaind init <moniker> --chain-id blackchain_20261120-1
cp testnet/blackchain-testnet-genesis.json ~/.blackchain/config/genesis.json
blackchaind genesis validate --home ~/.blackchain
```

### 4. Tambahkan seed / persistent peer (SETELAH seed publik diumumkan)

```bash
# Contoh format (GANTI dengan alamat seed publik yang diumumkan):
blackchaind start --home ~/.blackchain \
  --p2p.seeds "<node-id>@<IP-publik-seed>:26656" \
  --minimum-gas-prices 0abkc
```

Seed yang berlaku HARI INI hanya ada di `seeds.md` dan hanya berlaku
di VM lokal (127.0.0.1) — **jangan pakai alamat itu dari luar VM**,
tidak akan terjangkau.

### 5. Menjadi validator

Setelah node sinkron (`catching_up: false` di `curl localhost:26657/status`):

```bash
# Buat kunci + danai alamat staking (tBKC testnet dari faucet — faucet
# BELUM LIVE saat dokumen ini ditulis; ikuti pengumuman)
blackchaind keys add <nama-validator>
blackchaind tx staking create-validator \
  --amount 1000abkc --pubkey $(blackchaind tendermint show-validator) \
  --moniker <nama-validator> --commission-rate 0.05 \
  --commission-max-rate 0.20 --commission-max-change-rate 0.01 \
  --min-self-delegation 1000 --from <nama-validator> \
  --chain-id blackchain_20261120-1
```

Parameter validator (final, Sesi 4 + Sesi 7): active-set maks 100,
self-stake 1.000 BKC, slash double-sign 5% / downtime 1%, unbonding
21 hari, komisi min 5%, inflasi 0%. Insentif testnet: subsidi 10 tBKC/blok
selama 3 bulan, pagu 20 jt tBKC, pro-rata stake × uptime ≥ 95%
(`docs/06-validator-params.md` §5).

### 6. Coba transfer EVM

Tambahkan chain ke wallet (MetaMask): Chain ID `20261120` (hex
`0x1352900`), RPC URL endpoint publik (diumumkan setelah VPS tersedia),
simbol `BKC`, decimals 18. Transfer EVM pertama di rehearsal terbukti
(tx `0x562cf1…`, blok 6, +1.000.000 wei — `docs/17` §4).

## Yang BELUM bisa hari ini

- ❌ Terhubung ke jaringan live (tidak ada seed publik / IP publik)
- ❌ Klaim faucet (faucet belum diimplementasi — spec di `docs/13`)
- ❌ Jelajahi chain di BlackScan (belum diimplementasi — spec di `docs/11`)
- ❌ Tukar token di BlackSwap (belum ada kontrak — spec di `docs/12`)

## Yang SUDAH bisa hari ini

- ✅ Membaca & mengunduh paket testnet ini
- ✅ Membangun binary dari source dan menjalankan node sendiri dengan
  genesis yang sama (jaringan lokal sendiri)
- ✅ Mereproduksi rehearsal 4 validator dengan
  `scripts/setup-testnet-4val.sh` (semua 127.0.0.1, di satu mesin)
- ✅ Membaca semua bukti: sinkron 4 node, transfer EVM, liveness 3/4
  (`docs/17`), dan runbook peluncuran (`docs/18`)

## Pertanyaan / masalah

Buka issue di https://github.com/BlackchainLabs/blackchain/issues
dengan menyertakan: perintah yang dijalankan, output error lengkap,
dan versi binary (`blackchaind version`).
