#!/bin/bash
# Jalankan BlackScan Lite (Sesi 12). Bind 127.0.0.1:8081 (lokal saja).
# Stdlib Python saja — tanpa dependensi.
set -e
cd "$(dirname "$0")"
exec python3 blackscan.py
