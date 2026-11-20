# Auto-start BLACKCHAIN (systemd)

Keputusan pemilik (Teuku, 21 Nov 2026 ~02:28 WIB): auto-start JALAN — VM
sudah restart 4x (F34 ~00:28, ~01:41, ~01:46, ~02:27 WIB) dan tiap restart
mematikan semua node + faucet + BlackScan.

## Mekanisme yang dipilih: systemd SYSTEM units

- Unit SYSTEM di `/etc/systemd/system/` — satu unit per layanan + satu
  `blackchain.target` yang menarik semuanya, di-enable ke `multi-user.target`.
- **Bukan systemd user units**: di VM ini user bus TIDAK ada
  (`systemctl --user` → "Failed to connect to bus: No medium found",
  `loginctl` gagal, `systemd-logind` tidak aktif, tidak ada `user@.service`
  yang jalan). Unit user tidak akan pernah start.
- **Bukan cron**: tidak ada cron di VM ini (tidak ada binary `crontab`,
  tidak ada daemon cron).
- **Bukan supervisor lain**: tidak ada supervisor terpasang; systemd adalah
  PID 1 dan bus sistemnya berfungsi (`systemctl status` → running).

## Isi

| Unit | Layanan | Port |
|---|---|---|
| `blackchain-devnet.service` | devnet BKC (Jalur A) | RPC 26677, EVM 8555 |
| `blackchain-val1..4.service` | validator rehearsal 1–4 | RPC 26777/26787/26797/26807, EVM 8655/8665/8675/8685 |
| `blackchain-phase1.service` | devnet fork Fase 1 | RPC 26877, EVM 8755 |
| `blackchain-faucet.service` | faucet (After val1) | 8080 |
| `blackchain-blackscan.service` | BlackScan Lite (After val1) | 8081 |
| `blackchain.target` | menarik ke-8 layanan | — |

Setiap unit: `Restart=on-failure`, `RestartSec=10`, dibatasi
`StartLimitBurst=5` per 300 detik (bila crash berulang, systemd berhenti
mencoba — hook `blackchain-health-check` tetap menjadi backstop pemulihan).
`ExecCondition` berupa cek HTTP endpoint masing-masing: bila layanan sudah
menjawab (mis. sudah dipulihkan hook sebelum systemd start), unit dilewati
— tidak ada duplikat proses. Log mengikuti file log yang sudah dipakai
`scripts/restart-all-nodes.sh` (node: `*-node.log`, faucet/blackscan:
`repo/faucet/faucet.log`, `repo/blackscan/blackscan.log`).

Perintah start tiap unit SAMA PERSIS dengan `scripts/restart-all-nodes.sh`
(script itu tetap menjadi jalur pemulihan manual + jalur hook; systemd
adalah jalur boot). Faucet + BlackScan `After=blackchain-val1.service`
karena faucet butuh JSON-RPC val1 (127.0.0.1:8655).

## Pasang / perbarui

```bash
./repo/systemd/install.sh   # salin unit ke /etc/systemd/system, daemon-reload, enable
systemctl start blackchain.target   # mulai sekarang tanpa reboot
systemctl status blackchain.target  # lihat status semua layanan
systemctl list-dependencies blackchain.target
```

## Keterbatasan — baca ini

1. **`/etc` belum tentu bertahan saat VM diganti total.** File di `~`
   dijamin bertahan saat restart/replacement; file di `/etc` hanya bertahan
   selama VM yang sama di-reboot (bukti: unit runtime Hatch di `/etc`
   kembali hidup tiap restart F34). Bila suatu hari VM diganti dan unit
   hilang, jalankan lagi `./repo/systemd/install.sh` sekali — file sumber
   unit SELALU ada di repo ini (`repo/systemd/`), jadi instalasi bisa
   diulang kapan saja.
2. **Uji boot penuh belum dilakukan** — VM tidak di-reboot untuk pengujian
   ini (node live tidak boleh dimatikan). Yang sudah teruji: unit terpasang
   + ter-enable + `systemd-analyze verify` lolos, dan Restart otomatis
   terbukti pada faucet + BlackScan (proses di-kill → systemd
   menghidupkannya kembali, :8080/:8081 menjawab 200). Uji boot nyata
   terjadi saat VM restart berikutnya; hook `blackchain-health-check`
   tetap memantau tiap 60 detik dan memulihkan bila ada yang tidak naik.
3. Unit TIDAK mengubah konfigurasi chain, genesis, atau kunci validator.
