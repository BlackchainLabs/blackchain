# BLACKCHAIN — Jalur ke 100.000 TPS: Riset & Desain (Sesi 6, 2026-11-20)

**Status:** RISET & DESAIN — tidak ada kode yang diubah, tidak ada pengukuran
baru di sesi ini. Semua angka plafon di bawah adalah **ESTIMASI** (label
wajib), bukan hasil ukur, kecuali angka yang dikutip dari `docs/09` dan
sumber publik yang disebutkan. Tidak ada angka yang dikarang sebagai hasil
pengukuran BLACKCHAIN.

**Titik awal (TERUKUR, Sesi 4 — `docs/09-benchmark-tps.md`):** maksimum
**~89 TPS sustained (finalized)** di devnet lokal 1 validator (Cosmos SDK
v0.54.5 + Cosmos EVM v0.7.4, VM 1,5 CPU shared, 8 GB RAM). Jarak ke target
100.000 TPS: **~1.100×**.

## 0. Model throughput — kenapa 89 TPS, dan apa yang harus berubah

Throughput sistem ≈ nilai terkecil dari tiga pipa ini:

```
TPS ≈ min( laju ingest mempool ,  tx-per-blok / block time ,  laju eksekusi EVM )
```

| Pipa | Terukur di Sesi 4 | Keterangan |
|---|---|---|
| Ingest JSON-RPC + mempool Krakatoa | **~100–118 tx/detik** | `eth_sendRawTransaction` → unmarshal RLP → recover secp256k1 → cek nonce/saldo → insert mempool (lock). Efektif serial di 1,5 CPU. |
| tx-per-blok / block time | ~85–140 tx per blok @ block time efektif ~1,0 dtk | Biaya tetap per blok CometBFT (propose→prevote→precommit→commit + eksekusi + tulis disk) ~1,0 dtk di bawah beban, walau semua timeout 500ms (iterasi 4: plateau). |
| Eksekusi EVM | tidak diukur terpisah; bukan pembatas utama di 89 TPS | Cosmos EVM v0.7.4 mengeksekusi tx serial dalam satu blok. Transfer 21k gas dan contract call SSTORE mentok di angka yang sama → eksekusi bukan bottleneck pertama, TAPI akan menjadi bottleneck begitu ingest & blok diperbaiki. |

**Konsekuensi:** menaikkan satu pipa saja tidak menaikkan TPS sistem.
Target 100.000 TPS butuh SEMUA pipa naik ~1.000× secara bersamaan — atau
arsitektur yang mengubah bentuk pipanya (paralelisme, konsensus lain,
sharding). Gas limit blok BUKAN pembatas (`gasLimit` = 4.294.967.295;
100.000 transfer/detik × 21.000 gas × 0,4 dtk/blok = 840 jt gas/blok,
masih di bawah limit — tetapi angka ini hanya aritmetika, bukan bukti).

### Bukti pembanding dari chain lain (sumber publik, Nov 2026)

Angka-angka ini adalah klaim/ukuran pihak lain, BUKAN hasil BLACKCHAIN,
dan dipakai hanya sebagai kalibrasi kewajaran estimasi:

- **PEVM (RISE, Rust, Block-STM):** speedup 2–4× pada blok mainnet
  Ethereum nyata, sampai 22× pada workload sintetis yang sangat paralel.
- **Sei v2** (Cosmos SDK + CometBFT turunan + parallel EVM + "Twin-Turbo"
  consensus): plafon teoretis 12.500 TPS, finalitas <400ms; throughput
  mainnet terukur pada beban dApp nyata ~2.500–3.500 TPS (sumber:
  perbandingan 2026). Upgrade "Giga" menarget 200.000 TPS — target, bukan
  hasil.
- **Monad** (client EVM custom dari nol, MonadBFT HotStuff-family +
  eksekusi paralel optimistis + MonadDB): target 10.000 TPS, blok 0,4 dtk,
  finalitas 0,8 dtk; testnet memproses 2,44+ miliar tx; mainnet live
  Nov 2025.
- **Aptos** (Move + Block-STM): ~10.000 TPS terukur, plafon teoretis
  160.000 TPS.
- **Solana:** ~3.000–5.500 TPS sustained di mainnet (2026).

**Pelajaran:** bahkan tim besar dengan client custom dan waktu
bertahun-tahun mengukur 10³–10⁴ TPS pada beban nyata — bukan 10⁵.
Siapa pun yang mengklaim 100.000 TPS per chain tanpa benchmark
independen yang bisa direproduksi sedang menjual target sebagai hasil.

## 1. Pendekatan (a) — Eksekusi paralel gaya Block-STM / PEVM

**Cara kerja (singkat):** eksekusi optimistis — semua tx dalam satu blok
dijalankan serentak di banyak core dengan asumsi tidak saling
bergantungan; setiap tx mencatat read-set/write-set ke multi-version
memory; validator memeriksa konflik; tx yang konflik di-eksekusi ulang
dengan state yang benar. Hasil akhir harus IDENTIK dengan eksekusi
serial (determinisme adalah syarat konsensus).

**Masalah khas EVM** (kenapa port Block-STM ke EVM lebih sulit daripada
ke Move): semua tx dalam satu blok membaca/menulis akun beneficiary yang
sama (pembayaran gas) → secara naif semua tx "konflik". PEVM
menyelesaikannya dengan *lazy update* (pembayaran gas dicatat tanpa
membuat dependensi baca). Konflik nyata lain: nonce berurutan dari satu
pengirim, SSTORE ke slot yang sama (mis. counter, pool AMM populer),
saldo satu akun panas.

**Yang harus diubah di kode BLACKCHAIN:**
1. Fork Cosmos EVM v0.7.4 (atau tulis executor sendiri di atas
   `x/vm`): ganti loop eksekusi serial `DeliverTx` per blok dengan
   scheduler paralel (thread pool, mis. rayon-style di Go: goroutine +
   work-stealing).
2. Multi-version state: `StateDB` Cosmos EVM harus diganti/dibungkus
   dengan struktur yang mencatat versi per lokasi state + read/write
   set per tx, dan mendukung re-eksekusi deterministik.
3. Lazy update untuk beneficiary/gas dan (bila mungkin) untuk transfer
   saldo sederhana.
4. Validasi determinisme: dua node dengan core berbeda harus
   menghasilkan app-hash yang SAMA — ini syarat paling keras; satu bug
   nondeterminisme = chain split.
5. Uji regresi berat: replay blok mainnet Ethereum historis dan
   bandingkan state root dengan eksekusi serial.

**Risiko:** tertinggi di antara semua pendekatan. Bug determinisme =
chain halt/split. Fork Cosmos EVM = beban maintenance sendiri (tiap
rilis upstream harus di-rebase — lihat pelajaran Jalur C, Sesi 3).
Keuntungan paralelisme runtuh pada workload konflik tinggi (satu AMM
populer, satu NFT mint): speedup → ~1×.

**Plafon REALISTIS (ESTIMASI):** eksekusi saja naik 5–15× pada workload
campuran (kalibrasi: PEVM 2–4× blok nyata; Sei/Monad mencapai 10³–10⁴
TPS sistem dengan SEMUA pipa diperbaiki). Eksekusi paralel SAJA, tanpa
memperbaiki ingest & konsensus, menaikkan TPS sistem hampir NOL (pipa
lain tetap ~100 tx/detik). Dengan ingest + konsensus ikut diperbaiki:
kontribusi pendekatan ini ke sistem **ESTIMASI 2.000–10.000 TPS**.
Sendirian tidak membawa ke 100.000.

## 2. Pendekatan (b) — Ingest mempool paralel + JSON-RPC batching

**Ini bottleneck #1 yang terukur** (~100–118 tx/detik). Jalur tx masuk
hari ini: satu `eth_sendRawTransaction` → unmarshal RLP → recover
pengirim (secp256k1, mahal) → cek nonce/saldo via StateDB → insert ke
mempool Krakatoa (lock) → gossip ke peer. Semua serial per koneksi.

**Yang harus diubah di kode:**
1. **Admission paralel:** worker pool untuk `CheckTx` — recover
   signature + validasi dasar (format, gas, saldo, nonce) dijalankan
   paralel di N core; hanya insert ke mempool yang diserialisasi
   (lock singkat, atau sharding mempool per pengirim).
2. **Batch endpoint:** `eth_sendRawTransaction` batch (satu HTTP call,
   banyak tx) + `eth_sendTransaction` batch; kurangi overhead HTTP/TLS
   per tx.
3. **Beberapa node RPC di depan validator:** load balancer di atas
   2–4 node JSON-RPC khusus (non-validator) yang hanya admission +
   forward ke validator via mempool gossip / `BroadcastTx`. Satu
   validator tidak perlu melayani semua RPC.
4. **Urutan nonce dijaga:** tx dari satu pengirim harus masuk mempool
   dalam urutan nonce — admission paralel harus mengurutkan ulang per
   pengirim sebelum insert, atau menolak out-of-order dengan pesan yang
   jelas (client retry).
5. **Proteksi DoS:** rate limit per IP/pengirim, biaya admission
   (gas minimum), batas mempool per akun — tanpa ini, ingest paralel =
   permukaan serangan yang lebih lebar.

**Risiko:** sedang. Kompleksitas urutan nonce + duplikasi kerja antar
node RPC + DoS. Tidak menyentuh konsensus, jadi risiko chain split
rendah. Bisa dikerjakan bertahap dan diukur per langkah.

**Plafon REALISTIS (ESTIMASI):** ingest 10–50× → **1.000–5.000 tx/detik**
di server 16–32 core (kalibrasi: recover secp256k1 ~50–100 µs/tx/core
→ satu core ~10–20 ribu recover/detik secara teori; praktiknya StateDB
lookup + lock mempool yang membatasi — karena itu estimasi
konservatif 1–5 ribu, bukan 10 ribu). Setelah ingest naik, bottleneck
berikutnya langsung menjadi eksekusi + block time.

## 3. Pendekatan (c) — Konsensus sub-detik (tuning CometBFT → ganti konsensus)

**Fakta terukur:** tuning timeout CometBFT SUDAH HABIS (Sesi 4 iterasi
4: semua timeout 500ms → plateau 87–89 TPS; block time efektif tetap
~1,0 dtk di bawah beban). Satu-satunya timeout yang wajib ditunggu di
round sukses adalah `timeout_commit`; sisanya adalah batas atas, bukan
penentu. Biaya ~1 dtk/blok berasal dari: 3 round voting (propose →
prevote → precommit) + eksekusi + commit state ke disk + gossip antar
validator (di devnet 1 validator pun sudah ~0,67 dtk untuk blok kosong).

**Opsi bertahap (tanpa ganti konsensus):**
1. **Optimistic block processing** (pola Sei "Twin-Turbo"): validator
   mulai mengeksekusi blok SEGERA setelah menerima proposal, paralel
   dengan round prevote — waktu eksekusi "disembunyikan" di dalam
   waktu konsensus. Butuh fork CometBFT + jaminan rollback bila blok
   ditolak (>99,9% proposal lolos pada kondisi normal, menurut data Sei).
2. **Pipelining / vote extensions:** kirim precommit bersamaan dengan
   eksekusi; kurangi round-trip.
3. **Blok lebih besar, bukan blok lebih cepat:** naikkan `max_bytes` /
   `max_gas` per blok supaya tiap blok menampung lebih banyak tx —
   menaikkan TPS tanpa menaikkan laju blok (tetapi memperbesar biaya
   eksekusi per blok dan latensi gossip).
4. `create_empty_blocks = false` + interval — hanya relevan saat sepi,
   bukan saat beban.

**Opsi radikal (ganti konsensus):** HotStuff-family / pipelined BFT
(MonadBFT), atau DAG mempool + BFT (Narwhal/Tusk): memisahkan
penyebaran data (DAG) dari ordering, sehingga throughput data tidak
lagi dibatasi round voting. Ini pada praktiknya berarti MENULIS ULANG
lapisan konsensus — proyek multi-tahun, bukan tuning.

**Risiko:** sedang (tahap 1–3) sampai sangat tinggi (ganti konsensus).
Fork CometBFT = maintenance sendiri selamanya. Block time terlalu
agresif di jaringan validator geografis tersebar → round gagal, nil
prevote, liveness turun. Optimistic execution yang salah = state
divergen antar validator.

**Plafon REALISTIS (ESTIMASI):** blok 0,4 dtk yang NYATA (bukan hanya
timeout) + blok lebih besar → laju blok naik ~2,5× → kontribusi ke
sistem **ESTIMASI 200–500 TPS** bila pipa lain tetap, dan merupakan
pengali ~2–3× bila pipa lain sudah diperbaiki. Bukan jalan utama ke
100.000.

## 4. Pendekatan (d) — Kebutuhan hardware

**Fakta:** VM pengukuran Sesi 4: ~1,5 CPU shared, 8 GB RAM, disk 150 GB.
Semua bottleneck yang terukur (ingest serial, biaya blok) memburuk di
CPU kecil — tetapi hardware SAJA tidak cukup: pipa serial tetap serial
di CPU berapa pun (hukum Amdahl). Hardware adalah prasyarat pengukuran
yang bermakna, bukan solusi.

**Kebutuhan per peran (ESTIMASI — harus divalidasi dengan pengukuran
ulang di hardware tersebut):**

| Peran | CPU | RAM | Disk | Jaringan | Catatan |
|---|---|---|---|---|---|
| Devnet lokal (sekarang) | 1,5 shared | 8 GB | 150 GB | localhost | Cukup untuk fungsionalitas; TIDAK valid untuk klaim TPS. |
| Validator testnet (tahap 1–2) | 16 vCPU modern (≥3 GHz) | 64 GB | 2 TB NVMe (≥10k IOPS) | 1 Gbps, <100ms antar validator | Menampung ingest paralel + eksekusi paralel awal. |
| Validator performa (tahap 3) | 32–64 core | 128–256 GB | 4 TB NVMe (≥50k IOPS) | 10 Gbps | Untuk eksperimen eksekusi paralel skala penuh. |
| Node RPC / archive (BlackScan) | 8–16 vCPU | 32–64 GB | 4 TB+ NVMe (archive tumbuh terus) | 1 Gbps | Archive node menyimpan SEMUA state historis; disk adalah biaya utama. |
| Faucet / tooling | 2 vCPU | 4 GB | 50 GB SSD | 100 Mbps | Ringan; yang penting rate limit, bukan CPU. |

**Catatan:** disk IOPS penting karena commit state per blok (IAVL +
EVM state) adalah tulis sinkron; HDD atau disk shared lambat langsung
menjadi biaya per blok. RAM penting karena StateDB cache + mempool.
Semua angka hardware di atas adalah spesifikasi pengadaan, bukan hasil
ukur — validasi = benchmark ulang di hardware itu dan laporkan hasilnya.

## 5. Pendekatan (e) — Sharding / appchain horizontal

**Cara kerja:** bukan menaikkan TPS satu chain, melainkan menjalankan N
chain paralel (appchain Cosmos, masing-masing ~sama dengan BLACKCHAIN
hari ini) yang berkomunikasi via IBC/bridge. Throughput AGREGAT = N ×
TPS-per-chain.

**Yang harus diubah:** arsitektur multi-chain (koordinasi chain ID,
genesis per shard, router/bridge antar shard, likuiditas terfragmentasi
per shard, UX wallet yang tahu shard tujuan), plus keamanan bridge
antar shard (tanpa audit = risiko terbesar; lihat prinsip misi: bridge
tidak diluncurkan tanpa audit).

**Risiko:** tinggi di sisi keamanan & UX. Likuiditas terpecah (AMM di
shard A tidak melihat likuiditas shard B). Bridge adalah target
peretasan klasik. Kompleksitas operasional ×N.

**Plafon REALISTIS (ESTIMASI):** agregat 100.000 TPS butuh, mis. 100
chain × 1.000 TPS (setelah tahap 1–2) atau 1.000 chain × 100 TPS
(kondisi hari ini — tidak realistis secara operasional). Sharding
adalah pengali SETELAH per-chain TPS naik; sebagai jalan pintas dari
89 TPS ia menukar satu masalah sulit dengan N masalah sedang + satu
masalah keamanan besar. **Bukan 100.000 TPS per chain** — klaim harus
selalu menyebut "agregat", bila tidak maka menyesatkan.

## 6. Model gabungan — plafon per tahap (SEMUA ESTIMASI)

| Tahap | Yang dikerjakan | Plafon sistem (ESTIMASI) | Bukti yang dibutuhkan sebelum klaim |
|---|---|---|---|
| 0 — hari ini | — | **89 TPS terukur** | `docs/09` (sudah ada) |
| 1 — Fondasi | Hardware validator layak + ingest paralel (b) + blok lebih besar | **300–1.000 TPS** | Benchmark ulang `bench-evm.py` di hardware baru, 3 run |
| 2 — Eksekusi paralel | (a) Block-STM/PEVM di fork Cosmos EVM + optimistic processing (c) | **2.000–10.000 TPS** | Replay blok Ethereum nyata + benchmark beban kontrak konflik tinggi & rendah |
| 3 — Konsensus baru + storage | HotStuff/DAG (c radikal) + state DB paralel (MonadDB-style) | **10.000–50.000 TPS** | Testnet multi-validator ≥20 node, beban realistis berminggu-minggu |
| 4 — Sharding | (e) N appchain + IBC | **50.000–100.000+ TPS AGREGAT** | Ukur agregat lintas shard + audit bridge |
| — | 100.000 TPS **per chain** di stack Cosmos EVM | **TIDAK TERLIHAT dari bukti yang ada** | Butuh client EVM dari nol (pola Monad) + tim + waktu tahunan; bukan janji yang bisa dibuat hari ini |

Perkalian plafon di atas TIDAK bersifat aditif otomatis: setiap tahap
harus diukur ulang, karena bottleneck berpindah (ingest → eksekusi →
konsensus → storage → jaringan).

## 7. REKOMENDASI — satu pendekatan utama + urutan pengerjaan

**Pendekatan utama: (b) ingest paralel + hardware layak DULU, lalu (a)
eksekusi paralel Block-STM sebagai langkah penentu; (c) optimistic
processing sebagai fase 2; (e) sharding hanya sebagai pengali agregat
di akhir. (d) hardware adalah prasyarat di setiap tahap, bukan
pendekatan tersendiri.**

**Alasan:**
1. (b) menyerang bottleneck #1 yang TERUKUR (~100 tx/detik), risikonya
   paling rendah, hasilnya bisa diukur dalam hitungan minggu, dan
   setiap tahap berikutnya MEMBUTUHKAN ingest yang lebih cepat.
2. (a) adalah satu-satunya pendekatan yang menaikkan langit-langit
   eksekusi — tanpa ini, TPS sistem mentok di orde 10³ apapun yang
   dilakukan pada pipa lain. Bukti PEVM/Sei/Monad menunjukkan inilah
   jalan yang benar-benar ditempuh chain cepat.
3. (c) radikal (ganti konsensus) ditunda sampai (a)+(b) terbukti,
   karena biayanya terbesar dan manfaatnya hanya terasa setelah
   eksekusi paralel ada.
4. (e) ditunda paling akhir karena menukar masalah performa dengan
   masalah keamanan bridge + fragmentasi likuiditas.
5. **Yang TIDAK direkomendasikan:** mengejar 100.000 TPS per chain
   sebagai target jangka pendek, dan mengklaim angka apa pun sebelum
   ada benchmark yang bisa direproduksi.

**Urutan pengerjaan:**
1. **Fase 1 (minggu):** server validator layak (16 vCPU/64 GB/NVMe) →
   benchmark ulang baseline di hardware baru (E1) → ingest paralel +
   batch RPC (E2) → benchmark ulang.
2. **Fase 2 (bulan):** riset mendalam executor paralel: prototipe
   Block-STM di luar chain (replay blok Ethereum, ukur speedup vs
   serial) (E3) → bila speedup ≥3× pada blok nyata, integrasikan ke
   fork Cosmos EVM (E4) → uji determinisme lintas node (E5).
3. **Fase 3 (kuartal):** optimistic block processing + blok lebih besar
   (E6) → testnet multi-validator 20–30 node dengan beban realistis.
4. **Fase 4 (keputusan pemilik):** evaluasi ganti konsensus / sharding
   berdasarkan hasil Fase 2–3 — hanya bila bukti menunjukkan tahap
   1–3 tidak cukup.

## 8. Eksperimen terukur berikutnya (daftar E1–E6)

| ID | Yang diukur | Bagaimana | Kriteria lolos |
|---|---|---|---|
| E1 | Baseline di hardware layak | `bench-evm.py` (transfers + contract) di server 16 vCPU/64 GB/NVMe, 3 run tiap mode | Angka sustained + latensi p50/p95 tercatat di `docs/09` lanjutan |
| E2 | Ingest paralel | Worker pool CheckTx + batch RPC; ukur laju submit mentah (tx/detik) SEBELUM throughput chain | Laju submit ≥1.000 tx/detik tanpa kenaikan error |
| E3 | Speedup executor paralel (offline) | Prototipe Block-STM replay 100 blok mainnet Ethereum historis; bandingkan waktu vs serial + cocokkan state root | Speedup ≥3× & state root IDENTIK 100/100 blok |
| E4 | Executor paralel di chain | Fork Cosmos EVM + executor paralel; benchmark devnet 1 validator | TPS naik vs E1 tanpa tx gagal & tanpa app-hash divergen |
| E5 | Determinisme lintas node | 2 node (core berbeda) replay beban sama; bandingkan app-hash per height | 100% height cocok selama 1.000 blok |
| E6 | Konsensus sub-detik | Optimistic processing + blok 0,4 dtk di devnet 4 validator | Block time efektif ≤0,6 dtk di bawah beban + 0 round gagal |

**Tidak ada pengukuran baru di Sesi 6** — dokumen ini riset & desain;
semua eksperimen di atas BELUM dijalankan.

## 9. Keputusan yang dibutuhkan dari pemilik (blokir)

1. **Arah arsitektur ke 100.000 TPS** — setujui urutan Fase 1→4 di §7,
   atau pilih pendekatan lain (mis. langsung client custom gaya Monad,
   atau terima plafon tahap 1–2 sebagai target realistis).
2. **Anggaran hardware** — server validator tahap 1 (16 vCPU/64 GB/
   NVMe) + node RPC/archive: siapa yang menyediakan & membayar.
3. **Fork Cosmos EVM** — setujui bahwa eksekusi paralel berarti
   memelihara fork sendiri (biaya maintenance jangka panjang), atau
   tunggu upstream Cosmos EVM menyediakan eksekusi paralel.

## 10. Sumber (publik, diakses 20 Nov 2026)

- PEVM / Block-STM (RISE): docs.risechain.com — speedup 2–4× blok
  nyata, 22× sintetis; lazy update untuk beneficiary.
- Sei v2 (Twin-Turbo + parallel EVM): plafon teoretis 12.500 TPS,
  terukur ~2.500–3.500 TPS beban nyata; Giga menarget 200.000 TPS.
- Monad (MonadBFT + parallel execution + MonadDB): target 10.000 TPS,
  blok 0,4 dtk, finalitas 0,8 dtk; testnet 2,44+ miliar tx.
- Aptos Block-STM: ~10.000 TPS terukur.
- Solana mainnet sustained: ~3.000–5.500 TPS (2026).
- CometBFT configuration docs: `timeout_commit` adalah satu-satunya
  timeout yang wajib ditunggu di round sukses.
- Pengukuran BLACKCHAIN sendiri: `docs/09-benchmark-tps.md` (Sesi 4).
