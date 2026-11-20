# BLACKCHAIN — Monitoring & Incident Plan (P6) (Sesi 12, 2026-11-20)

**Status:** IMPLEMENTASI JALAN (skrip) + RUNBOOK ini. Prasyarat P6 dari
`docs/18` kini terpenuhi di tingkat rehearsal lokal.
Kode: `repo/monitoring/health-check.py` (stdlib saja).
Status terakhir: `repo/monitoring/data/status.json` (di-gitignore).

## 1. Monitoring yang jalan

### 1.1 Health-check (tiap menit — cron dipasang Muse utama)

```cron
* * * * * /usr/bin/python3 /home/hatch/workspace/blackchain/repo/monitoring/health-check.py >> /home/hatch/workspace/blackchain/repo/monitoring/data/health.log 2>&1
```

Perintah di atas BELUM dipasang sebagai cron oleh Sesi 12 (penjadwalan
di tangan Muse utama) — skrip sudah teruji 2x run manual (lihat §2).
Skrip hanya MEMBACA RPC/HTTP; tidak mengubah node apa pun.

### 1.2 Yang dicek tiap run

| Cek | Sumber | Ambang |
|---|---|---|
| Height + hash + `catching_up` + jumlah peer tiap node | CometBFT RPC devnet 26677, val1–4 26777/26787/26797/26807 | — |
| EVM hidup + `eth_chainId` = `0x1352900` | EVM 8555 (devnet), 8655/8665/8675/8685 | chain ID salah = CRITICAL |
| HALT | height sama dengan run sebelumnya | CRITICAL |
| FORK | validator hidup beda hash di height sama | CRITICAL |
| Kuorum | <3 dari 4 validator hidup | WARNING (butuh >2/3) |
| Faucet | `8080/api/status` | DOWN = WARNING; saldo <100 BKC = WARNING |
| BlackScan | `8081/api/health` + `/api/v2/stats` | DOWN/lag >10 blok = WARNING |

### 1.3 Output

- `data/status.json` — status terakhir (level OK/WARNING/CRITICAL, height
  tiap node, daftar masalah). Exit code: 0 OK, 1 WARNING, 2 CRITICAL.
- `data/prev.json` — height run sebelumnya (untuk deteksi halt).
- Satu baris ringkas per run ke stdout/log:
  `2026-11-20T17:35:28Z OK devnet=11359 val=923/923/923/923 problems=0`.

## 2. Hasil uji (perintah + output nyata)

```
$ python3 repo/monitoring/health-check.py
2026-11-20T17:35:28Z OK devnet=11359 val=923/923/923/923 problems=0
exit=0
$ python3 repo/monitoring/health-check.py   # 4 detik kemudian
2026-11-20T17:35:32Z OK devnet=11364 val=924/924/924/924 problems=0
exit=0
```

- Semua node UP, keempat validator height 923 hash SAMA
  `2531A37A…`, masing-masing 3 peer, `catching_up: false`.
- Faucet UP (saldo 9.899,9999 BKC, 1 klaim); BlackScan UP
  (`indexed_height` 923 = head, lag 0).
- Tidak ada false positive halt: height naik antar-run (923→924).

## 3. Runbook insiden

Prinsip: **jangan panik, jangan restart semua sekaligus, jaga kuorum 3/4.**
Selalu cek `data/status.json` + log node dulu sebelum bertindak.
Pemilik tiap langkah: operator (Muse) untuk langkah teknis; Teuku
(pemilik) untuk keputusan yang ditandai **[PEMILIK]**.

### 3.1 Satu validator DOWN (RPC tidak menjawab)

1. Cek proses: `ps aux | grep blackchaind | grep val<N>`.
2. Cek log: `~/workspace/blackchain/logs/restart-sesi12-val<N>.log`
   (atau log awal node) — cari baris error terakhir.
3. Bila proses mati dan tidak ada error korupsi data: start ulang node
   itu saja dengan `scripts/restart-local-nodes.sh`
   (skrip melewati node yang sudah jalan).
4. Verifikasi: height node itu mengejar (`catching_up: true` lalu
   `false`) dan hash sama dengan 3 validator lain.
5. Bila node tidak mau start / error database: JANGAN hapus data dulu —
   laporkan ke pemilik dengan pesan error lengkap. **[PEMILIK]** bila
   perlu reset node (kehilangan riwayat lokal validator itu; chain tetap
   jalan dengan 3 validator).

### 3.2 Chain HALT (height diam >2 menit di ≥3 node)

1. Konfirmasi: jalankan health-check 2x berjarak 60 detik; cek
   `catching_up` dan log tiap node.
2. Periksa penyebab umum: (a) satu validator double-sign/ter-jail,
   (b) disk penuh (`df -h`), (c) memori habis, (d) jam sistem melompat.
3. Bila 3 validator hidup tapi tidak ada blok baru: JANGAN restart
   ketiganya bersamaan. Restart SATU validator (yang log-nya paling
   bersih), tunggu 60 detik, cek height.
4. Bila tetap halt: kumpulkan log 4 node + `status.json` dan laporkan
   ke pemilik. **[PEMILIK]** memutuskan: lanjut diagnosa atau
   regenesis darurat (langkah terakhir — semua riwayat rehearsal hilang).

### 3.3 FORK (hash berbeda di height sama)

1. JANGAN panik: di CometBFT, fork sejati hampir mustahil setelah commit
   (finalitas instan). Yang umum: satu node tertinggal (height beda) —
   itu BUKAN fork, itu lag; atau satu node menjalankan binary/config
   berbeda.
2. Bandingkan: height + hash + `app_hash` tiap node; node yang
   menyimpang diidentifikasi dari `status.json`.
3. Node menyimpang: stop, periksa `config.toml`/`genesis.json`-nya
   (hash genesis harus sama dengan yang lain), lalu start ulang —
   ia akan sync ulang dari peer.
4. Bila 2 kelompok hash bertahan (fork nyata): stop SEMUA validator,
   laporkan ke pemilik dengan bukti hash. **[PEMILIK]** memutuskan
   jalur pemulihan (pilih cabang mayoritas / regenesis).

### 3.4 Seed node (VPS) DOWN — saat sudah ada

1. Cek dari VM ini: SSH ke VPS (bila bisa) → `systemctl status
   blackchaind-seed` → `journalctl -u blackchaind-seed -n 100`.
2. Restart service: `systemctl restart blackchaind-seed`; verifikasi
   `curl localhost:26657/status` di VPS.
3. Rantai lokal TIDAK tergantung seed VPS (validator lokal tetap jalan)
   — yang hilang hanya jalur masuk validator eksternal.
4. Bila VPS tidak bisa di-SSH sama sekali: laporkan ke pemilik
   (cek panel provider: status, firewall port 22/26656). **[PEMILIK]**.

### 3.5 VM/runtime restart — SEMUA proses mati (F34, sudah terjadi 2026-11-20)

1. Gejala: semua RPC tidak menjawab, `ps` kosong.
2. Jalankan `scripts/restart-local-nodes.sh` (4 validator + devnet).
   Node melanjutkan dari height di disk — TIDAK perlu regenesis.
3. Verifikasi: keempat validator height sama + hash sama;
   devnet height naik.
4. Restart layanan: faucet (`repo/faucet/start.sh`), BlackScan
   (`repo/blackscan/start.sh`) — state klaim + index bertahan di disk.
5. Node fork Phase 1: MILIK Sesi 9 — jangan di-restart sendiri;
   beri tahu Sesi 9 / Muse utama.
6. Jalankan health-check 2x; catat kejadian di mission log sebagai
   insiden (bukan kegagalan kode).
7. **Pencegahan (SELESAI 21 Nov 2026 — auto-start):** unit systemd
   SYSTEM `blackchain-*.service` + `blackchain.target` di
   `/etc/systemd/system/` (sumber: `repo/systemd/`, pasang ulang via
   `repo/systemd/install.sh`); semua layanan start otomatis saat boot
   + `Restart=on-failure` bila crash. Detail + keterbatasan:
   `repo/systemd/README.md`. Sisa terbuka: backup berkala
   `priv_validator_key.json` terenkripsi offline (butuh keputusan
   pemilik).

### 3.6 Faucet habis / faucet DOWN

- DOWN: cek proses faucet (`ps` + `repo/faucet/faucet.log`), restart
  dengan `systemctl restart blackchain-faucet.service` (kini dikelola
  systemd; systemd juga me-restart otomatis bila crash — `repo/faucet/start.sh`
  tetap bisa dipakai manual bila systemd tidak aktif). Kunci diekspor ulang ke memori saat start.
- Habis (saldo <100 BKC): JANGAN isi ulang diam-diam — lihat
  `docs/22` §2 (opsi unbond / transfer genesis / regenesis).
  **[PEMILIK]** memilih opsi + menyetujui sumber dana.

### 3.7 BlackScan lag / DOWN

- DOWN: cek proses + `repo/blackscan/blackscan.log`, restart
  `systemctl restart blackchain-blackscan.service` (kini dikelola
  systemd; `repo/blackscan/start.sh` tetap bisa dipakai manual bila
  systemd tidak aktif); indexer backfill otomatis dari height
  terakhir di SQLite.
- Lag >10 blok: cek `GET /api/health` (`indexer_error`); cek RPC val1
  (8655) hidup atau tidak. Bila DB rusak: hapus
  `repo/blackscan/data/blackscan.db*` → backfill ulang dari blok 1
  (cepat, ~900 blok).

## 4. Kontak & eskalasi

| Situasi | Tindakan | Pemilik keputusan |
|---|---|---|
| 1 validator down | Restart node itu ( §3.1) | Operator |
| Halt / fork | Diagnosa + laporkan (§3.2/§3.3) | Teuku bila regenesis |
| Semua proses mati (F34) | `restart-local-nodes.sh` (§3.5) | Operator |
| VPS/seed down | Restart service / cek panel (§3.4) | Teuku (akses panel) |
| Faucet habis | Jangan isi ulang sendiri (§3.6) | Teuku (sumber dana) |
| Dana treasury / distribusi / burn | TIDAK PERNAH tanpa persetujuan eksplisit | Teuku |

## 5. Hal terbuka

1. Cron tiap menit (§1.1) belum dipasang — dipasang Muse utama.
2. Alerting keluar (Telegram/email) belum ada — health-check hanya
   menulis file + exit code. Butuh keputusan pemilik (saluran + siapa
   menerima).
3. Auto-start systemd pasca-restart VM (§3.5 butir 7) — SELESAI 21 Nov 2026 (unit di `repo/systemd/`, terpasang + ter-enable; uji Restart terbukti pada faucet + BlackScan; uji boot penuh baru saat VM restart berikutnya).
4. Backup kunci validator terenkripsi offline (belum ada jadwal).
