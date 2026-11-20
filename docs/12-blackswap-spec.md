# BLACKCHAIN — Spesifikasi BlackSwap (DEX AMM) v0.1 (Sesi 6, 2026-11-20)

**Status:** SPESIFIKASI — belum ada kode, belum ada deploy, belum ada
audit. TIDAK ADA aset nyata di testnet. Semua angka fee/parameter di
bawah adalah USULAN spesifikasi, bukan keputusan final — perubahan butuh
persetujuan pemilik.

## 1. Keputusan dasar

| Keputusan | Pilihan | Alasan |
|---|---|---|
| Model AMM | Constant product **x · y = k** (Uniswap V2-style) | Paling sederhana, teruji, paling mudah diaudit; cocok untuk testnet pertama. Kurva concentrated liquidity (V3-style) DITUNDA ke fase 2. |
| Pasangan awal (testnet) | **tBKC / tUSDC** (keduanya token testnet, tanpa nilai) | BKC adalah aset native; stablecoin testnet dibutuhkan sebagai pasangan harga. tUSDC adalah token ERC-20 mock yang di-mint faucet — BUKAN USDC asli, TIDAK bisa di-redeem. |
| Fee swap | **0,30%** (0,25% ke LP + 0,05% protokol) | Standar Uniswap V2; porsi protokol masuk treasury testnet (HANYA dengan persetujuan governance; di testnet awal dapat diset 0%). |
| Kontrak | Factory + Pair + Router, Solidity, OpenZeppelin v5.7.0 | Pola yang sama dengan kontrak vesting (Sesi 5): OZ untuk Ownable/ReentrancyGuard; audit WAJIB sebelum mainnet. |
| Jaringan | Testnet BLACKCHAIN dulu; mainnet HANYA setelah audit | — |

## 2. Kontrak (ruang lingkup)

| Kontrak | Fungsi | Catatan keamanan |
|---|---|---|
| `BlackSwapFactory` | Membuat pair, menyimpan `feeTo` (penerima fee protokol), `feeToSetter` (owner) | Owner = multisig/timelock (keputusan pemilik, lihat §7). |
| `BlackSwapPair` (ERC-20 LP token) | Menyimpan reserve, mint/burn LP, swap dengan invariant x·y=k, TWAP oracle (cumulative price) | `ReentrancyGuard` di mint/burn/swap; cek `K` tidak turun; batas reserve. |
| `BlackSwapRouter` | `addLiquidity`, `removeLiquidity`, `swapExactTokensForTokens`, `swapTokensForExactTokens`, deadline, `amountOutMin` | Semua fungsi `nonReentrant`; validasi deadline & slippage di router, bukan di UI saja. |
| `BlackSwapOracle` (opsional, fase 2) | TWAP dari cumulative price pair | TWAP rentan manipulasi bila likuiditas kecil — JANGAN dipakai sebagai oracle harga tunggal untuk pinjaman. |

**Tidak termasuk di v0.1:** limit order, concentrated liquidity,
flash loan, farming/staking LP, routing multi-hop otomatis (router
hanya single-hop dulu; multi-hop fase 2).

## 3. Mekanika AMM

- **Harga:** `harga = reserve_out / reserve_in` (sebelum fee).
- **Output swap:** `amountOut = (amountIn × 997 × reserveOut) /
  (reserveIn × 1000 + amountIn × 997)` — fee 0,30% (997/1000).
- **Price impact:** `impact = amountIn / (reserveIn + amountIn)` —
  ditampilkan di UI SEBELUM konfirmasi; swap DITOLAK bila impact
  melewati batas yang diset pengguna.
- **Slippage:** default toleransi **0,5%** di UI; pengguna bisa ubah
  0,1%–5,0%; transaksi revert bila `amountOut < amountOutMin`.
- **Deadline:** default 20 menit dari submit; transaksi kedaluwarsa
  revert (melindungi dari tx yang dieksekusi di harga lama).
- **Likuiditas awal:** LP pertama menetapkan harga awal; LP mendapat
  token LP = `sqrt(amountA × amountB) − 1000` (1000 unit terkunci
  selamanya ke alamat nol, pola Uniswap V2, mencegah inflasi LP).
- **Minimum liquidity:** pair dengan total supply LP < ambang
  (diusulkan 1.000 LP unit) dianggap tidak likuid — UI memberi
  peringatan keras.

## 4. Perlindungan MEV (dasar — v0.1)

Jujur dicatat: **BlackSwap v0.1 TIDAK kebal MEV.** Yang disediakan
adalah mitigasi dasar:

1. **Slippage + deadline** (§3) — membatasi kerugian dari sandwich
   attack; bukan menghilangkannya.
2. **Peringatan di UI:** tampilkan price impact & rute; peringatkan
   bila impact >3% atau likuiditas pair < ambang.
3. **Tidak ada private mempool / Flashbots-style di v0.1** — mempool
   BLACKCHAIN bersifat publik; siapa pun bisa melihat tx pending di
   BlackScan.
4. **Fase 2 (riset):** commit-reveal, batch auction, atau integrasi
   dengan proposer-builder separation — semuanya butuh perubahan
   konsensus/mempool, TIDAK dijanjikan di v0.1.
5. **Dokumentasi risiko:** halaman "Risiko" di UI menjelaskan
   frontrunning & sandwich dalam bahasa sederhana (Indonesia +
   Inggris).

## 5. Token testnet & likuiditas awal

- **tBKC:** didapat dari faucet (lihat `docs/13`); 1 tBKC = 1 BKC
  testnet (denom `abkc` di-wrap menjadi ERC-20 `tBKC` oleh kontrak
  `WBKC` — pola WETH — karena pair AMM butuh ERC-20, bukan coin native).
- **tUSDC:** token mock ERC-20 (6 desimal, mengikuti USDC) yang
  di-mint oleh faucet; TIDAK memiliki nilai, TIDAK dapat ditebus.
- **Likuiditas awal testnet:** disediakan tim dari alokasi komunitas
  testnet (jumlah & alamat pendanaan BUTUH keputusan pemilik —
  lihat §7 dan `docs/14`). Tanpa likuiditas awal, pair tidak bisa
  dipakai; tanpa batas, likuiditas awal bisa dimanipulasi — tetapkan
  jumlah di dokumen pendanaan terpisah sebelum deploy.
- **Harga awal tBKC/tUSDC:** ditetapkan oleh rasio likuiditas awal
  (mis. 1 tBKC = 1 tUSDC sebagai harga awal simbolis testnet —
  keputusan pemilik; harga testnet TIDAK mencerminkan harga mainnet).

## 6. Pengujian & audit (wajib)

| Tahap | Isi | Kriteria |
|---|---|---|
| Unit test (Foundry) | invariant x·y=k, fee, slippage, deadline, LP mint/burn, reentrancy | 100% fungsi kritis ter-cover; 0 gagal |
| Fuzz / invariant test | Foundry invariant: K tidak pernah turun (kecuali fee), reserve ≥ 0, LP supply konsisten | 10.000+ run tanpa pelanggaran |
| Testnet soak | pair live 2 minggu, volume simulasi, pantau price impact & error | 0 insiden kehilangan dana testnet di luar skenario uji |
| Audit independen | audit eksternal SEBELUM mainnet & SEBELUM ada aset nyata | Semua temuan high/critical diperbaiki + re-audit bila perlu |

**Aturan keras:** BlackSwap TIDAK menerima aset nyata / mainnet
sebelum audit selesai. Testnet = token tanpa nilai saja.

## 7. Hal terbuka (butuh keputusan pemilik)

1. Alamat owner Factory (`feeToSetter`): EOA vs multisig vs timelock.
2. Fee protokol 0,05%: aktif (masuk treasury) atau 0% di testnet.
3. Jumlah & sumber likuiditas awal tBKC/tUSDC testnet.
4. Harga awal simbolis tBKC/tUSDC.
5. Jadwal audit & anggaran audit sebelum mainnet.
6. Apakah pair tambahan (mis. tBKC/tETH) dibuka di testnet, dan oleh siapa.
