# BLACKCHAIN — Implementasi Faucet Testnet v0.1 (Sesi 12, 2026-11-20)

**Status:** IMPLEMENTASI JALAN (bukan spek lagi). Spek awal: `docs/13-faucet-validator-onboarding.md` §A.
Kode: `repo/faucet/` (`faucet.py`, `start.sh`, `README.md`).
Server live: `127.0.0.1:8080` (lokal saja), proses faucet aktif sejak 2026-11-20 17:25 UTC.

## 1. Arsitektur

```
Pengguna → GET / (form) → GET /api/challenge → PoW di browser
        → POST /api/claim → verifikasi PoW + cooldown + limit IP
        → sign EVM tx (kunci val1, hanya di memori)
        → eth_sendRawTransaction → val1 EVM 127.0.0.1:8655
        → tunggu receipt → catat claims.json + claims.log
```

- Stack: Python 3.12 stdlib `http.server` + `eth_account` (venv
  `~/workspace/blackchain/venvs/faucet`, di luar repo — tidak di-push).
- Satu file server (`faucet.py`, ~400 baris). Tanpa database, tanpa dependensi berat.
- Klaim diserialisasi dengan lock global; nonce diambil fresh dari `pending`;
  retry maks 3x bila nonce bertabrakan.

## 2. Dana faucet — FAKTA (bukan asumsi)

| Item | Nilai | Sumber |
|---|---|---|
| Alamat pengirim | `0x7C54D93649524Ad774125a9e8E03B1BC1043238c` (alamat ETH validator val1) | `eth_getBalance` 8655 |
| Saldo cair saat dibangun | **9.999,999987882526 BKC** | `eth_getBalance` 2026-11-20 17:25 UTC |
| Kapasitas efektif | **~99 klaim** @100 tBKC | 9.999,9999 / 100 |
| Pool faucet genesis | 10.000.000 tBKC — **STAKED (bonded), BUKAN cair** | `genesis/blackchain-testnet-genesis.json` + saldo EVM |

Penjelasan: genesis memberi val1 total 30.010.000 BKC, tetapi 30.000.000 BKC
di antaranya terikat sebagai self-delegation staking (20 jt pool subsidi +
10 jt pool faucet). Saldo cair val1 hanya 10.000 BKC, berkurang jadi
~9.999,9999 BKC oleh transfer uji Sesi 8 + klaim uji Sesi 12.
**Konsekuensi:** faucet ini hanya melayani ~99 klaim sebelum habis.
Mengisi ulang butuh keputusan pemilik — pilihannya: (a) unbond sebagian
stake val1 (unbonding 21 hari, mengurangi keamanan rehearsal), (b) transfer
dari alamat genesis lain yang cair (val2/val3/val4 masing-masing 10.000 BKC),
atau (c) regenesis testnet publik dengan alokasi faucet cair. Opsi (c)
adalah yang direkomendasikan untuk testnet publik yang serius (sejalan
dengan catatan `docs/18` §8).

## 3. Aturan klaim (diimplementasikan)

| Aturan | Nilai | Implementasi |
|---|---|---|
| Jumlah per klaim | 100 tBKC | `AMOUNT_WEI = 100 * 10**18` |
| Cooldown alamat | 24 jam | `claims.json`, dicek sebelum kirim |
| Rate limit IP | 5 klaim / IP / 24 jam | IP disimpan sebagai SHA-256 (bukan IP mentah) |
| Batas harian global | 1.000.000 tBKC | dicek sebelum kirim (di atas saldo cair) |
| Anti-Sybil | PoW `sha256(alamat:challenge:nonce)` diawali `0000` | challenge sekali pakai, kedaluwarsa 10 menit |
| Gas | `eth_gasPrice` dari chain (saat ini 0x0) | dibaca live, bukan hardcode |

**Yang TIDAK ada (jujur):** hCaptcha / Turnstile — butuh layanan eksternal +
site key + koneksi keluar dari browser pengguna; belum diputuskan pemilik
(`docs/13` A.3 butir 1). PoW ringan hanya menaikkan biaya bot, bukan
jaminan anti-Sybil. Tier verifikasi GitHub/X (`docs/13` A.3 butir 5) TIDAK
aktif (default sesuai spek).

## 4. Kunci & keamanan

- Kunci pengirim = kunci `validator` val1 (keyring `test`,
  home `testnet-data/val1`). Diekspor ke memori saat start dengan perintah
  yang sama seperti `scripts/testnet-transfer-test.py` (Sesi 8).
- Private key **tidak pernah** ditulis ke file, log, atau laporan.
  Yang tercatat hanya alamat pengirim (publik) + tx hash.
- Server bind `127.0.0.1:8080` — tidak bisa diakses dari luar VM ini.
  Ekspos publik butuh reverse proxy + TLS + rate limit — keputusan pemilik.
- Faucet TIDAK pernah meminta seed phrase / private key pengguna;
  hanya alamat `0x...` (sesuai `docs/13` A.3 butir 7).

## 5. Uji end-to-end (perintah + output nyata)

Uji dijalankan 2026-11-20 17:25 UTC dengan alamat baru sekali pakai
`0x97D002845112b7d5DcfC093Ed7f27c58D2615460` (kunci dibuat di proses uji
dan dibuang — bukan kunci faucet):

```
saldo sebelum: 0 wei
PoW nonce: 54039
klaim 1 HTTP 200 -> {"ok": true,
  "tx_hash": "0x8dfe2e3c9b8aded52b03e6c85027cf60553143c320d4d99488a3558d0158e53c",
  "amount_bkc": 100, "block": 829, "next_claim_at": 1795281930}
saldo sesudah: 100000000000000000000 wei = 100.0 tBKC
klaim 2 HTTP 400 -> {"ok": false, "error": "cooldown",
  "message": "Alamat ini sudah klaim. Coba lagi dalam 24.0 jam."}
riwayat: {"claimed_before": true, "count": 1,
  "tx_hash": "0x8dfe2e3c...58e53c", "next_claim_at": "2026-11-21T17:25:30+00:00"}
UJI FAUCET: LOLOS
```

Replikasi antar-node (bukti tx masuk ke chain, bukan hanya val1):

```
# eth_getTransactionReceipt di val2 EVM (8665):
{"blockNumber": "0x33d", "status": "0x1",
 "from": "0x7c54d93649524ad774125a9e8e03b1bc1043238c",
 "to": "0x97d002845112b7d5dcfc093ed7f27c58d2615460",
 "transactionHash": "0x8dfe2e3c...58e53c"}
# eth_getBalance penerima di val2: 0x56bc75e2d63100000 (= 100 * 10^18 wei)
```

Status endpoint saat uji:

```
GET /api/status -> {"chain_id": 20261120,
  "faucet_address": "0x7C54D93649524Ad774125a9e8E03B1BC1043238c",
  "faucet_balance_bkc": 9999.999987882526, "amount_per_claim_bkc": 100,
  "cooldown_hours": 24, "ip_daily_max": 5, "spent_today_bkc": 0.0,
  "global_daily_cap_bkc": 1000000.0, "total_claims": 0, ...}
```

(nilai `spent_today_bkc` 0.0 tercatat SEBELUM klaim uji; setelah klaim: 100.0.)

## 6. Operasional

- Start: `cd repo/faucet && ./start.sh` (atau `nohup ./start.sh > faucet.log 2>&1 &`).
- Stop: `pkill -f 'faucet.py'` — JANGAN pakai `pkill blackchaind` (itu mematikan node).
- Data klaim: `repo/faucet/data/claims.json` + `claims.log` (di-gitignore).
- Bila faucet habis (`faucet_empty`): isi ulang hanya atas keputusan pemilik
  (lihat §2) — jangan ambil dari treasury / alamat lain tanpa persetujuan.

## 7. Hal terbuka (butuh keputusan pemilik)

1. Pengisian ulang faucet saat saldo cair habis (§2 — opsi a/b/c).
2. hCaptcha / Turnstile untuk testnet publik (site key + penyedia).
3. Ekspos publik (reverse proxy + TLS) — saat ini lokal saja.
4. Alokasi tBKC faucet final untuk testnet publik (`docs/13` A.6 butir 1).
