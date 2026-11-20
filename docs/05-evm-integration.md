# Integrasi EVM — Hasil Uji Kompatibilitas (20 Nov 2026, Sesi 2)

## Ringkasan jujur
- **EVM BELUM terintegrasi ke `blackchaind`.** Devnet lokal yang jalan
  adalah Cosmos SDK murni (tanpa modul EVM, tanpa JSON-RPC Ethereum).
- **Bukan karena kurang usaha:** dua kandidat upstream dicoba dan keduanya
  mentok di ketidakcocokan versi yang terbukti dari `go.mod` resmi,
  bukan tebakan.

## Kandidat 1 — Ethermint klasik (`github.com/evmos/ethermint`)
- `go.mod` terakhir: Cosmos SDK **v0.50.6**.
- Scaffold BLACKCHAIN: SDK **v0.55.0**. Selisih 5 minor → DITOLAK.

## Kandidat 2 — Cosmos EVM (`github.com/cosmos/evm`, penerus resmi evmOS)
Rilis dan SDK yang ditarget (dibaca dari `go.mod` tiap rilis):
| Cosmos EVM | SDK yang ditarget |
|---|---|
| v0.5.1 | v0.53.5 (pseudo) |
| v0.6.5 | v0.53.6 |
| v0.7.4 | **v0.54.3** (paling baru) |
| v1.0.0-rc2 | v0.53.0 |

**Tidak ada rilis Cosmos EVM yang menarget SDK v0.55.0.**
Perubahan nama modul: `x/evm` → `x/vm`; format chain ID Ethermint
(`evmos_9001-2`) tidak lagi dipakai.

## Uji empiris (salinan terpisah `~/workspace/.build-tmp/evm-trial`)
1. `go get github.com/cosmos/evm@v0.7.4` → exit 0.
2. `go mod tidy` → exit 0. SDK tetap v0.55.0 (MVS).
3. Probe `x/evmprobe` (blank import `x/vm/keeper` + `x/feemarket/keeper`):
   - **Gagal #1:** `eips/eips.go: GetConstantGas/SetConstantGas undefined`
     pada `vm.operation`. Penyebab: `replace` go-ethereum Cosmos EVM
     (`github.com/ethereum/go-ethereum => github.com/cosmos/go-ethereum
     v1.17.2-cosmos-0`) tidak bersifat transitif — modul utama harus
     menambahkannya sendiri. Perbaikan: `go mod edit -replace ...` →
     error ini hilang. DIPERBAIKI.
   - **Gagal #2 (MENTOK):** `x/vm/types/msg.go:208: undefined:
     signingtypes.SignMode_SIGN_MODE_TEXTUAL`.
     Penyebab persis: `cosmossdk.io/api v1.1.0` (yang dipakai SDK v0.55)
     **menghapus** `SIGN_MODE_TEXTUAL` dari enum
     `cosmos.tx.signing.v1beta1.SignMode` — CHANGELOG api v1.1.0:
     "Remove the `cosmos/msg/textual/v1` package and the
     `SIGN_MODE_TEXTUAL` value … Enum number 2 and the name are reserved."
     (PR cosmos-sdk #26456). Cosmos EVM v0.7.4 masih memakai simbol itu
     di `msg.go:208` (`keyringSigner.SignByAddress(..., TEXTUAL)`).
     Ini inkompatibilitas upstream SDK v0.55 vs Cosmos EVM, bukan
     kesalahan konfigurasi BLACKCHAIN.

## Jalur penyelesaian yang tersisa (pilih satu, butuh keputusan Teuku)
- **A (direkomendasikan): turunkan scaffold ke SDK v0.54.3** — SDK
  native Cosmos EVM v0.7.4 — lalu integrasi `x/vm` + `x/feemarket`
  + ante handler + JSON-RPC. Konsekuensi: scaffold ulang (Ignite v30
  menghasilkan SDK 0.55), devnet SDK 0.55 yang sudah jalan harus
  dibangun ulang di 0.54.3. Estimasi: satu sesi kerja penuh.
- **B: tunggu rilis Cosmos EVM untuk SDK v0.55** — belum ada per
  20 Nov 2026 (rilis terbaru v1.0.0-rc2 masih SDK v0.53.0).
- **C: fork Cosmos EVM dan patch `msg.go:208`** (ganti TEXTUAL → DIRECT)
  — bisa jalan, tapi fork harus dirawat sendiri dan mengubah perilaku
  signing; tidak dilakukan diam-diam tanpa persetujuan.

## Yang sudah terbukti di sesi ini (di luar EVM)
- `go build ./...` scaffold exit 0; `go test ./x/blackchain/...` ok
  (keeper 0.076s, types 0.185s).
- Devnet lokal `blackchain-1` 1 validator memproduksi blok (height 131
  saat dicek 18:40 WIB, `catching_up: false`).
