# BLACKCHAIN — Testnet Rehearsal Multi-Validator (Sesi 8, 2026-11-20)

**Status:** REHEARSAL BERHASIL — jaringan 4 validator berjalan di VM lokal
(127.0.0.1), BUKAN testnet publik. Tidak ada node yang bisa diakses dari
internet; tidak ada IP publik, domain, atau DNS. Lihat
`docs/18-testnet-launch-package.md` untuk apa yang masih kurang agar
menjadi publik.

**Binary:** `build/blackchaind-sdk54-bkc` (Cosmos SDK v0.54.5 + Cosmos EVM
v0.7.4). **Chain:** `blackchain_20261120-1`, EVM chain ID 20261120
(`0x1352900`), denom `abkc`. **Setup:**
`repo/scripts/setup-testnet-4val.sh` (+ `repo/scripts/eth_bech32.py`,
`repo/scripts/testnet-transfer-test.py`). **Homes:**
`workspace/blackchain/testnet-data/val{1,2,3,4}`.
**Genesis final (draft):** `repo/genesis/blackchain-testnet-genesis.json`
(tervalidasi, lihat §4).

## 1. Topologi rehearsal

Semua node di 127.0.0.1 (VM yang sama). Tiap validator self-stake 1.000
BKC (gentx), voting power sama (1e15 unit).

| Validator | Staking (secp256k1) | ETH (ethsecp256k1) | Node ID (P2P) | RPC / P2P / gRPC / REST / EVM / WS |
|---|---|---|---|---|
| val1 | `black1qa4gujwn2q787axaqge90m7zs9ns5m2w4wq8fy` | `0x7c54d93649524ad774125a9e8e03b1bc1043238c` | `9088193266bf7fe1addf21ea42dfa8c5b3ff97a2` | 26777 / 26776 / 9202 / 1338 / 8655 / 8656 |
| val2 | `black1fjl4r2xppll4apr794gmqtztv3c5mvt5a6e7ku` | `0xa3888f5b5c7946d8992b95af1db372b8c3c206b9` | `1cc0f94349707b4f3a9ac8b69e3c40fec9010f32` | 26787 / 26786 / 9203 / 1339 / 8665 / 8666 |
| val3 | `black1uzn7a8pylxgft5vx4y5d0nwulucalq2kwv35w7` | `0xa6e72f8cef4af06b79fb60595b0ec4d9b8896113` | `7e7320fa5271e2c9cec93ecb0dc74d495b1fc80e` | 26797 / 26796 / 9204 / 1340 / 8675 / 8676 |
| val4 | `black1xqjdsfpy9lt44g8nv2qnrqrqn9yvg2m0ct8yt9` | `0x7e6432fcb84b903449efd785f4f198b03260c34d` | `fcae4c9ecb0a8635c7b2b1352d1ab8579e9bca84` | 26807 / 26806 / 9205 / 1341 / 8685 / 8686 |

Priv-validator (Tendermint): val1 `D7E40900…`, val2 `3D2A683F…`, val3
`29482EBB…`, val4 `EC98B78E…` (awalan 8 hex; kunci privat TIDAK dicatat).
Semua kunci adalah kunci TESTNET lokal tanpa nilai (keyring `test`).

## 2. Alokasi genesis (testnet, tanpa nilai)

Total supply genesis: **30.080.000 BKC** (30.080.000 × 10^18 abkc =
30.080.000.000.000.000.000.000.000 abkc), jauh di bawah max supply
1 miliar BKC (`mint.max_supply` = 10^27 abkc, inflasi 0).

| Akun | Jumlah | Keterangan |
|---|---|---|
| val1 staking | 30.010.000 BKC | 10.000 BKC milik validator + **20.000.000 tBKC pool subsidi testnet** (pagu `docs/06` §5) + **10.000.000 tBKC pool faucet** — dipegang alamat operator SELAMA rehearsal; SEBELUM pembukaan publik WAJIB dipindah ke community pool / multisig lewat gov. Bukan alokasi tim/mainnet. |
| val2/val3/val4 staking | 10.000 BKC masing-masing | Saldo validator (self-stake gentx 1.000 BKC) |
| val1–val4 ETH | 10.000 BKC masing-masing | Saldo EVM (akun `ethsecp256k1`, wajib ada agar StateDB melihat saldo — pelajaran F17) |
| Tim / mainnet | 0 | TIDAK ADA alokasi tim/mainnet di genesis testnet ini |

Parameter (sama seperti devnet BKC Sesi 4): max validator 100,
min. commission 5%, unbonding 21 hari, slash double-sign 5% / downtime
1%, window 100 blok, jail 600 dtk, gov min. deposit 10 BKC, inflasi 0%.

## 3. Bukti (a) — keempat node sinkron

Blok pertama: height 1, waktu 2026-11-20T16:08:52.906634014Z, 0 tx,
hash `DBE87FE5ED4316C8D42CBF8CBFC96E0AA1D4F8DF0C527512AB98A128E88E992E`,
chain_id `blackchain_20261120-1`.

Pengamatan 2026-11-20 ~16:09 UTC (25 dtk setelah start):

| Node | Height | Hash | catching_up | Peers |
|---|---|---|---|---|
| val1 | 4 | `0AC715175CF7890A` | false | 3 |
| val2 | 4 | `0AC715175CF7890A` | false | 3 |
| val3 | 4 | `0AC715175CF7890A` | false | 3 |
| val4 | 4 | `0AC715175CF7890A` | false | 3 |

Pengamatan lanjutan: height 15, hash `CE18B6B4F3218D5C` di keempat node
(setelah restart val4, lihat §6); height 18, hash `550A9A61814C8CA9`
(val1, saat dokumen ini ditulis — jaringan terus membuat blok).

EVM: `eth_chainId` = `0x1352900` (20261120) dan `eth_blockNumber`
cocok dengan height CometBFT di keempat endpoint (8655/8665/8675/8685).

## 4. Bukti (b) — transfer EVM terkonfirmasi di semua node

Skrip: `repo/scripts/testnet-transfer-test.py` (kunci validator
di-export IN-MEMORY via `keys export --unarmored-hex --unsafe -y`;
kunci TIDAK pernah dicetak/disimpan).

- Pengirim: `0x7C54D93649524Ad774125a9e8E03B1BC1043238c` (ETH val1)
- Penerima: `0xE85241d28a4E5837dC49586aC60158200E4596A9` (akun baru sekali pakai)
- Nilai: **1.000.000 wei**, gas 21000, gasPrice 578.307.829.000 wei
  (total biaya gas 12.117.474.571.000 wei)
- **tx hash: `0x562cf1f23ebc3ef5e6b73df4111def7fa555a0321013b879880c38f5dde08350`**
- Receipt: blok 6, status `0x1` (sukses), gasUsed 21000
- Saldo pengirim: 10.000.000.000.000.000.000.000 → 9.999.999.987.882.525.429.000
  wei (delta −12.117.474.571.000 = nilai + gas, cocok persis)
- Saldo penerima: 0 → **1.000.000 wei** (delta persis +1.000.000)
- Verifikasi silang: receipt blok 6 + status `0x1` + saldo penerima
  1.000.000 wei TERLIHAT SAMA di keempat endpoint EVM
  (8655, 8665, 8675, 8685). Transfer pertama di jaringan 3-validator
  (tx `0x26b0b556…`, blok 14) juga lolos di ketiga node saat itu —
  jaringan 3-validator diganti 4-validator sebelum uji liveness (F33).

## 5. Bukti (c) — liveness: 1 validator mati, blok tetap jalan

- Height sebelum val4 dimatikan: **7** (PID val4: 12802, dimatikan
  dengan `kill`, proses berhenti, RPC 26807 mati — terverifikasi).
- Setelah ~25 dtk dengan val4 MATI (3/4 validator aktif = 75% daya >
  2/3): val1/val2/val3 di **height 10, hash `FF42BAC904B71D04`,
  catching_up false** — blok BERTAMBAH (7 → 10). Liveness TERBUKTI.
- val4 di-restart dengan perintah start yang sama; ~25 dtk kemudian
  keempat node di **height 15, hash `CE18B6B4F3218D5C`,
  catching_up false** — val4 mengejar ketertinggalan (catch-up)
  dan kembali sinkron penuh.

## 6. Kegagalan yang diperbaiki (F32–F33)

- **F32 — konsensus macet di height 1 (jaringan 3-validator pertama).**
  Gejala: val1↔val3 terhubung (1 peer), val2 0 peer, semua node stuck
  height 1 round 0 step 4 (precommit), proposer height 1 (val2) tidak
  pernah menyampaikan proposal. Log: `auth failure: secret conn
  failed: EOF` (dial val2) + `Inbound Peer rejected: duplicate CONN`
  (val1/val3). Penyebab: `allow_duplicate_ip = false` (default) —
  ketiga node berbagi IP 127.0.0.1, sehingga switch CometBFT menolak
  koneksi kedua dari IP yang sama. Perbaikan: `allow_duplicate_ip =
  true` + `addr_book_strict = false` di `config.toml` ketiga node
  (pengaturan KHUSUS rehearsal lokal; node publik dengan IP routable
  berbeda memakai default). Hasil: 3 node langsung sinkron (height 4,
  hash sama). Perbaikan diabadikan di `scripts/setup-testnet-4val.sh`.
- **F33 — liveness 2/3 dengan 3 validator setara TIDAK MUNGKIN
  (matematika BFT, bukan bug).** Gejala: val3 dimatikan di height 16,
  setelah 20 dtk val1/val2 TETAP di height 16 — chain halt, tanpa fork
  dan tanpa blok invalid. Penyebab: 3 validator berdaya sama → 2
  validator = tepat 2/3 daya, sedangkan CometBFT butuh kuorum
  **> 2/3** (strictly greater). Dengan n=3, toleransi fault f=0.
  Perbaikan: jaringan dibangun ulang dengan **4 validator** (3/4 =
  75% > 2/3), lalu uji liveness di §5 lolos. Pelajaran untuk testnet
  publik: jumlah validator genesis minimal 4; idealnya 5–7 agar 1–2
  validator mati tidak menghentikan chain.

Kegagalan kecil lain (diperbaiki tanpa nomor F): `keys export` butuh
`--unsafe -y` (selain `--unarmored-hex`); `eth_sendRawTransaction`
menolak raw tx tanpa prefix `0x`; skrip setup pertama gagal karena
`cp` genesis ke dirinya sendiri (val1) dan karena alamat staking
val2/val3 belum didanai sebelum gentx (F32a — gentx memvalidasi
saldo akun; diperbaiki dengan mendanai keempat alamat staking +
keempat alamat ETH di genesis).

## 7. Status node saat dokumen ditulis

Keempat node testnet rehearsal MASIH BERJALAN (PID start 16:06–16:08
UTC, 20 Nov 2026) di port §1, height terus bertambah. Devnet BKC
1-validator lama (JSON-RPC 8555) tetap jalan terpisah dan TIDAK
dipakai untuk rehearsal ini. Node rehearsal HANYA mendengarkan
127.0.0.1 — tidak ada port yang dibuka ke internet.
