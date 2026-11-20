#!/usr/bin/env bash
# Pasang unit systemd BLACKCHAIN (auto-start setelah VM reboot).
# Idempotent: aman dijalankan ulang — hanya menyalin unit, reload, enable.
# JANGAN jalankan dengan sudo bila sudah root (VM ini berjalan sebagai root).
# Penggunaan: ./repo/systemd/install.sh
# Verifikasi: systemctl is-enabled blackchain.target
#             systemctl status blackchain-devnet blackchain-val1 blackchain-faucet blackscan 2>/dev/null
#             systemctl list-dependencies blackchain.target
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
DST="/etc/systemd/system"

for f in "$SRC"/blackchain-*.service "$SRC"/blackchain.target; do
  install -m 0644 "$f" "$DST/$(basename "$f")"
  echo "pasang: $DST/$(basename "$f")"
done

systemctl daemon-reload
systemctl enable blackchain.target \
  blackchain-devnet.service blackchain-val1.service blackchain-val2.service \
  blackchain-val3.service blackchain-val4.service blackchain-phase1.service \
  blackchain-faucet.service blackchain-blackscan.service
echo "OK — blackchain.target enabled; semua layanan start otomatis saat boot."
echo "Mulai sekarang (tanpa reboot): systemctl start blackchain.target"
