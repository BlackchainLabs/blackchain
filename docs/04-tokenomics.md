# BLACKCHAIN — Tokenomics BKC v0.1 (DRAFT, Month 1, 20 Nov 2026)

**Status:** DRAFT — parameter diusulkan, belum disahkan governance, belum ada
kontrak yang di-deploy.
**Penulis:** Tokenomics Research AI.

## 1. Fakta tetap (dari misi)

- Max supply: **1.000.000.000 BKC** (1e27 unit terkecil, 18 desimal).
- Komunitas: **95% = 950.000.000 BKC**.
- Tim development: **5% = 50.000.000 BKC**.
- Vesting tim: **12 bulan**, jadwal publik, claim contract transparan.
- Tidak ada alokasi tersembunyi, tidak ada minting tanpa otorisasi, tidak ada
  inflasi supply di luar aturan konsensus yang disetujui.

## 2. Verifikasi aritmetika

| Alokasi | BKC | Unit terkecil (wei) |
|---|---|---|
| Komunitas (95%) | 950.000.000 | 950.000.000 × 10^18 = 9,5 × 10^26 |
| Tim dev (5%) | 50.000.000 | 50.000.000 × 10^18 = 5 × 10^25 |
| **Total** | **1.000.000.000** | **1 × 10^27** |

Dicek dengan Python saat penulisan dokumen ini: 950.000.000 + 50.000.000 =
1.000.000.000 — konsisten.

## 3. Rincian komunitas 95% (DIUSULKAN — belum final)

Pembagian di bawah ini adalah **usulan**, bukan keputusan. Totalnya harus
tetap 950.000.000 BKC.

| Kategori | Usulan | BKC |
|---|---|---|
| Airdrop testnet & kontributor awal | 20% dari total supply | 200.000.000 |
| Reward validator / staking (emisi bertahap) | 40% dari total supply | 400.000.000 |
| Ekosistem & grants developer | 20% dari total supply | 200.000.000 |
| Bug bounty & keamanan | 5% dari total supply | 50.000.000 |
| Cadangan komunitas / treasury DAO | 10% dari total supply | 100.000.000 |
| **Total komunitas** | **95%** | **950.000.000** |

## 4. Vesting tim 5% (diusulkan)

- Cliff: 3 bulan setelah mainnet (diusulkan).
- Linear vesting: 12 bulan total sejak mainnet.
- Claim via smart contract transparan; jadwal publik di dashboard supply.
- **Belum ada kontrak vesting yang di-deploy.** Draft spesifikasi kontrak ada
  di whitepaper Bab 12. Deploy ke Sepolia HANYA setelah review Security
  Auditor AI.

## 5. Airdrop — kriteria kelayakan (diusulkan)

Diberikan untuk kontribusi nyata: partisipan testnet, operator validator,
peneliti bug bounty, developer, kontributor ekosistem, partisipasi komunitas
yang genuine. Anti-Sybil: analisis pola on-chain + bukti kontribusi
(mis. PR merged, laporan bug valid, uptime validator) — tanpa mengecualikan
partisipan sah secara arbitrer. Detail skoring anti-Sybil BELUM dirancang;
ini pekerjaan Month 2.

## 6. Buyback & burn bulanan (aturan, bukan eksekusi)

- Laporan keuangan bulanan, monitoring saldo treasury, kebijakan buyback
  yang disetujui, catatan eksekusi transparan, transaksi burn yang bisa
  diverifikasi, pengurangan supply permanen, review treasury independen.
- **Tidak ada transaksi treasury, buyback, atau burn yang dieksekusi dalam
  misi ini.** Tidak ada janji apresiasi harga atau return investor.
- Semua eksekusi butuh persetujuan governance eksplisit dari Teuku.

## 7. Yang belum diputuskan

- Laju emisi reward validator per blok/tahun.
- Komisi validator dan pembagian reward delegator.
- Persentase slash yang tepat.
- Alamat treasury & vesting contract (TIDAK BOLEH diisi alamat palsu —
  dibiarkan kosong sampai dibuat lewat proses resmi).
