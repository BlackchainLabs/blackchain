# BLACKCHAIN — Parameter Validator & Emisi (keputusan testnet, Sesi 4, 2026-11-20)

Dokumen ini menetapkan parameter validator yang masuk akal untuk testnet
BLACKCHAIN, alasan tiap nilai, dan apa yang sudah diterapkan di devnet lokal
identitas BKC (`blackchain_20261120-1`, chain ID EVM 20261120, denom `abkc`).

## Ringkasan keputusan

| Parameter | Nilai | Keterangan |
|---|---|---|
| Active-set size (`max_validators`) | **100** | Standar Cosmos Hub; cukup besar untuk desentralisasi testnet, cukup kecil untuk finality cepat 1 validator di devnet |
| Minimum self-stake | **1 abkc** (`min_self_delegation` di gentx) | SDK 0.54 tidak lagi punya parameter `min_self_delegation` global; self-bond ditetapkan per validator saat `gentx`/`create-validator`. Devnet: self-bond 1.000 BKC (10^21 abkc). Untuk testnet publik, tetapkan minimum self-stake **1.000 BKC** sebagai aturan operasional (bukan parameter konsensus) — validator di bawah itu tidak diterima di genesis |
| Slash double-sign | **5%** (`slash_fraction_double_sign = 0.05`) | Standar Cosmos Hub |
| Slash downtime | **1%** (`slash_fraction_downtime = 0.01`) | Standar Cosmos Hub |
| Downtime window | 100 blok, min. signed 50%, jail 600 dtk | Standar Cosmos Hub |
| Unbonding time | 21 hari (1.814.400 dtk) | Standar Cosmos Hub; cermin mainnet |
| Min. commission rate | **5%** (`min_commission_rate = 0.05`) | Mencegah race-to-zero; validator gentx default 10% masih di atasnya |
| Emisi / inflasi | **0%** (inflasi min/maks/rate-change = 0) | BKC bersuplai TETAP 1 miliar; tidak ada pencetakan baru |
| Max supply (mint module) | **10^27 abkc = 1.000.000.000 BKC** | Batas keras di modul mint; sesuai tokenomics |
| Blocks per year | 6.307.200 (blok 5 dtk) | Untuk perhitungan tahunan mint/distribusi |
| Reward validator | **Hanya dari fee transaksi** (EIP-1559: base fee dibakar, tip ke proposer/validator via distribusi) + alokasi komunitas bila diputuskan governance | Tanpa inflasi, keamanan jangka panjang bergantung pada volume fee — ini trade-off yang disadari (lihat Risiko) |
| Gov min. deposit | 10 BKC | Cukup rendah untuk testnet |
| Gov expedited min. deposit | 50 BKC | Harus > min. deposit (validasi genesis) |

## Alasan

1. **100 validator** — angka yang dipakai Cosmos Hub dan sebagian besar chain
   Cosmos. Di atas 100, overhead gossip/voting CometBFT naik tanpa manfaat
   keamanan yang sepadan untuk testnet; di bawah 100 (mis. 21), testnet
   terlihat terpusat. Testnet bisa dimulai dengan 20–30 validator aktif
   dan membiarkan set tumbuh sampai 100.
2. **Slash 5% / 1%** — mengikuti praktik Cosmos Hub yang sudah teruji.
   Double-sign 5% cukup menyakitkan untuk mencegah equivocation; downtime
   1% cukup ringan agar validator testnet yang tidak stabil tidak langsung
   bangkrut, tapi tetap ada konsekuensi.
3. **Inflasi 0%** — tokenomics BKC menetapkan max supply 1 miliar dengan
   alokasi 950 jt komunitas / 50 jt tim. Mencetak BKC baru via mint akan
   melanggar janji itu. Konsekuensinya: reward validator HANYA dari fee.
   Bila fee testnet terlalu kecil untuk menarik validator, opsinya (butuh
   keputusan governance/pemilik): (a) alokasi reward dari porsi komunitas
   yang dijadwalkan, (b) inflasi kecil sementara di testnet saja, atau
   (c) subsidi validator dari treasury testnet. JANGAN diam-diam mengubah
   inflasi tanpa keputusan tercatat.
4. **Min. commission 5%** — mencegah validator menawarkan 0% untuk
   memonopoli delegasi lalu menaikkan tarif setelahnya.

## Yang diterapkan di devnet BKC

Semua nilai di atas sudah diterapkan di genesis devnet identitas BKC
(`devnet-data-bkc/cosmos/config/genesis.json`) dan tervalidasi
(`genesis validate` OK) sebelum start ulang bersih 2026-11-20 15:12 UTC.
Perintah penerapan: `scripts/setup-bkc-devnet.sh` (bagian edit genesis).

Pengecualian yang dicatat: `min_self_delegation` bukan parameter genesis di
SDK 0.54 — self-bond 1.000 BKC diterapkan lewat `gentx` (nilai `value`
10^21 abkc). Aturan minimum self-stake 1.000 BKC untuk testnet publik
adalah kebijakan operasional, bukan penegakan konsensus.

## Risiko & hal terbuka (butuh keputusan pemilik)

- **Keamanan berbasis fee saja** — bila volume transaksi testnet rendah,
  imbal hasil validator ~0 dan hanya operator yang termotivasi ideologis
  yang bertahan. Pantau dan putuskan skema insentif sebelum testnet publik.
- **Slashing di testnet** — downtime 1% + jail 600 dtk bisa membuat
  validator pemula frustrasi. Untuk testnet publik awal, pertimbangkan
  downtime slash 0,1% sementara (perlu keputusan; mengubahnya butuh
  proposal gov atau genesis baru).
- **Jumlah validator awal** — testnet dimulai 1 validator (devnet) dan
  harus tumbuh bertahap; kriteria penerimaan validator (identitas,
  uptime, self-stake) belum ditetapkan.
