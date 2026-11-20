# BLACKCHAIN — Parameter Validator & Emisi (Sesi 4 + revisi Sesi 7, 2026-11-20)

Dokumen ini menetapkan parameter validator yang masuk akal untuk testnet
BLACKCHAIN, alasan tiap nilai, dan apa yang sudah diterapkan di devnet lokal
identitas BKC (`blackchain_20261120-1`, chain ID EVM 20261120, denom `abkc`).

**Revisi Sesi 7 (keputusan pemilik, disampaikan lewat Muse utama):** skema
insentif validator hibrida dua fase kini DIPUTUSKAN (bagian 5). Parameter
konsensus Sesi 4 tidak berubah.

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
| Reward validator | **Hibrida dua fase — DIPUTUSKAN Sesi 7** (lihat §5): testnet = subsidi blok dari community pool + fee; mainnet = fee (tip) + 50% fee protokol BlackSwap. BUKAN inflasi. | Fixed supply 1 miliar tetap dijaga |
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
   melanggar janji itu. Konsekuensinya: reward validator HANYA dari fee
   dan subsidi yang dananya sudah dialokasikan di genesis (bukan dari
   pencetakan baru).
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

## 5. Skema insentif validator — DIPUTUSKAN Sesi 7 (keputusan pemilik)

Model **hibrida dua fase**: subsidi sementara di testnet, lalu murni
berbasis fee di mainnet. Inflasi tetap 0% di kedua fase — subsidi testnet
bukan pencetakan baru, melainkan alokasi genesis dari bucket reward
validator yang sudah ada di tokenomics (`docs/04` §3).

### 5.1 Fase testnet — subsidi blok + fee

| Parameter | Nilai | Alasan |
|---|---|---|
| Tarif subsidi | **10 tBKC per blok** | Lihat perhitungan di bawah; cukup besar untuk terlihat, cukup kecil untuk tidak menguras alokasi |
| Durasi | **3 bulan testnet** (90 hari = 1.555.200 blok @ 5 dtk/blok) | Sejalan dengan rencana testnet 3 bulan; cukup lama untuk menguji stabilitas validator |
| Total subsidi bila penuh | **15.552.000 tBKC** (10 × 1.555.200) | Di bawah pagu — lihat baris berikut |
| Pagu testnet | **20.000.000 tBKC** (pagu keras) | = 5% dari bucket reward validator 400 jt BKC (`docs/04` §3), = 2% dari total supply. Subsidi BERHENTI bila pagu tercapai, walau 3 bulan belum habis |
| Sumber dana | Community pool, dari alokasi genesis bucket "Reward validator / staking" | Dana sudah dicetak di genesis (bagian dari max supply 1 miliar); bukan mint baru |
| Mekanisme pencairan | Tarif per blok diakru, **dibayar bulanan** lewat proposal community-pool spend, pro-rata berdasarkan **stake × uptime** validator aktif pada bulan itu | Tidak butuh modul custom baru di Sesi 7 — memakai `x/distribution` community pool yang sudah ada di Cosmos SDK. Modul subsidi per-blok otomatis adalah pekerjaan implementasi terpisah bila diinginkan |
| Syarat penerima | Validator aktif di set (termasuk di 100 besar), uptime ≥ 95% pada bulan berjalan, self-stake ≥ 1.000 BKC | Mencegah validator "tidur" ikut menerima subsidi; selaras dengan downtime window 100 blok |
| Akhir subsidi (sunset) | Otomatis berakhir di akhir bulan ke-3 testnet ATAU saat pagu 20 jt tBKC tercapai — mana yang lebih dulu | Tidak ada perpanjangan diam-diam |

**Perhitungan per validator (ilustrasi, bukan janji):** bila 25 validator
aktif dengan stake dan uptime kurang-lebih merata, tiap validator menerima
~15.552.000 / 25 ≈ **622.000 tBKC selama 3 bulan** (~6.900 tBKC/hari).
Bila set penuh 100 validator merata, ~155.500 tBKC per validator selama
3 bulan. Token testnet (tBKC) **tidak punya nilai** — subsidi ini adalah
insentif partisipasi dan pengujian, bukan penghasilan.

**Perpanjangan:** hanya boleh diperpanjang **sekali, maksimal 1 bulan**,
dengan tarif yang sama atau lebih rendah, dan HANYA lewat keputusan
pemilik yang tercatat (proposal gov / dokumen keputusan). Perpanjangan
tanpa batas adalah inflasi terselubung dan DILARANG oleh aturan misi ini.

### 5.2 Fase mainnet — fee + fee protokol BlackSwap, tanpa subsidi

| Sumber pendapatan validator | Keterangan |
|---|---|
| Tip transaksi (EIP-1559) | Base fee dibakar; tip masuk ke proposer/validator via distribusi. Sumber utama bila volume tinggi |
| **50% fee protokol BlackSwap** | Fee protokol BlackSwap = 0,05% dari volume swap (`docs/12`). Setengahnya (0,025% dari volume) dialirkan ke pool reward validator; setengah lainnya (0,025%) ke treasury (dana buyback & burn). Pembagian 50/50 adalah keputusan Sesi 7; ditinjau ulang 6 bulan setelah mainnet |
| Komisi delegasi | Min. 5%, default gentx 10%; validator menetapkan sendiri di atas minimum |
| Subsidi blok | **TIDAK ADA** di mainnet — subsidi testnet berakhir sebelum mainnet |

**Ilustrasi (bukan proyeksi pendapatan):** bila volume BlackSwap mainnet
mencapai 1.000.000 BKC/hari, fee protokol = 500 BKC/hari, bagian validator
= 250 BKC/hari untuk seluruh set. Angka ini KECIL bila volume rendah —
itulah risiko yang disadari (lihat §5.3). Imbal hasil validator mainnet
bergantung pada volume transaksi + volume swap, bukan pada janji.

### 5.3 Risiko & mitigasi

| Risiko | Mitigasi |
|---|---|
| Subsidi testnet habis sebelum volume naik → validator pergi saat transisi ke mainnet | Sunset diumumkan sejak hari pertama testnet; validator bergabung dengan ekspektasi yang jelas. Transisi diumumkan ≥ 30 hari sebelum akhir subsidi. Mainnet TIDAK diluncurkan sebelum ada bukti volume fee yang cukup untuk set validator minimum (kriteria: ≥ 20 validator aktif bertahan 30 hari tanpa subsidi di testnet akhir — diukur, bukan diasumsikan) |
| Subsidi menarik operator "tBKC farmer" yang tidak peduli keamanan | Syarat uptime ≥ 95% + self-stake 1.000 BKC; slash downtime tetap berlaku; validator yang di-slash kehilangan hak subsidi bulan itu |
| Pembagian fee BlackSwap diperebutkan governance | Pembagian 50/50 ditulis di dokumen ini dan di `docs/12`; perubahan butuh proposal gov + persetujuan pemilik |
| Volume mainnet rendah → imbal hasil validator ~0 | Jujur sejak awal: mainnet dengan fee-only hanya aman bila ada volume. Bila volume tidak tercapai, opsinya adalah MENUNDA mainnet, bukan mencetak BKC baru. Inflasi permanen tetap DILARANG tanpa revisi tokenomics yang disetujui pemilik |

## Risiko & hal terbuka

- **Slashing di testnet** — downtime 1% + jail 600 dtk bisa membuat
  validator pemula frustrasi. Untuk testnet publik awal, pertimbangkan
  downtime slash 0,1% sementara (perlu keputusan; mengubahnya butuh
  proposal gov atau genesis baru).
- **Jumlah validator awal** — testnet dimulai 1 validator (devnet) dan
  harus tumbuh bertahap; kriteria penerimaan validator (identitas,
  uptime, self-stake) kini ditetapkan di §5.1.
- **Implementasi pencairan subsidi** — mekanisme bulanan via community
  pool adalah desain Sesi 7; skrip perhitungan pro-rata (stake × uptime)
  dan template proposal gov adalah pekerjaan implementasi berikutnya.
