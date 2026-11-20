# BLACKCHAIN Testnet Faucet v0.1 (Sesi 12)

Server faucet minimal yang **benar-benar jalan** melawan rehearsal testnet
lokal (4 validator, EVM JSON-RPC val1 `127.0.0.1:8655`, chain ID 20261120).

## Menjalankan

```bash
./start.sh            # bind 127.0.0.1:8080, log ke stdout
```

Butuh venv `~/workspace/blackchain/venvs/faucet` (Python 3.12 + `eth-account`).
Kunci validator val1 diekspor **ke memori saja** saat start
(`blackchaind keys export ... --unarmored-hex --unsafe -y`, pola Sesi 8);
tidak pernah ditulis ke disk/log.

## Aturan klaim

| Aturan | Nilai |
|---|---|
| Jumlah per klaim | 100 tBKC |
| Cooldown | 24 jam per alamat |
| Rate limit IP | 5 klaim / IP / 24 jam |
| Batas harian global | 1.000.000 tBKC (di atas saldo cair) |
| Anti-Sybil | Proof-of-work ringan `sha256(alamat:challenge:nonce)` diawali `0000` — **bukan** hCaptcha (butuh layanan eksternal + site key; keputusan pemilik) |

## Endpoint

| Endpoint | Fungsi |
|---|---|
| `GET /` | Halaman web klaim (PoW di browser) |
| `GET /api/status` | Saldo faucet, kuota harian, total klaim |
| `GET /api/challenge?address=0x...` | Minta challenge PoW |
| `POST /api/claim` | Body `{address, challenge, nonce}` → `{tx_hash, block}` atau error |
| `GET /api/claims/<address>` | Riwayat klaim alamat + kapan boleh klaim lagi |

## Dana faucet (fakta, 2026-11-20)

- Pengirim: `0x7C54D93649524Ad774125a9e8E03B1BC1043238c` (alamat ETH validator val1).
- Saldo cair saat dibangun: **~9.999,9999 BKC** → kapasitas efektif **~99 klaim** @100 tBKC.
- Pool faucet 10.000.000 tBKC di genesis berstatus **STAKED (bonded), bukan cair**
  — tidak bisa dipakai tanpa unbonding 21 hari / keputusan pemilik.
  Isi ulang faucet = keputusan pemilik (lihat `docs/22-faucet-implementation.md`).

## Data

- `data/claims.json` — riwayat klaim (alamat → klaim terakhir, tx hash).
- `data/claims.log` — log penyaluran append-only (alamat, IP hash SHA-256, tx hash, blok).
- `data/` di-gitignore — tidak ikut commit.

## Uji end-to-end (Sesi 12, 2026-11-20 17:25 UTC)

- Alamat uji baru `0x97D00284...15460`: saldo 0 → klaim 1 → **+100 tBKC**
  (tx `0x8dfe2e3c9b8aded52b03e6c85027cf60553143c320d4d99488a3558d0158e53c`,
  blok 829, status 0x1; receipt + saldo terverifikasi juga di val2 EVM 8665).
- Klaim ke-2 dalam 24 jam: **DITOLAK** (`cooldown`, coba lagi dalam 24,0 jam).
- Detail lengkap: `docs/22-faucet-implementation.md`.
