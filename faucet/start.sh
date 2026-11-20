#!/bin/bash
# Jalankan faucet BLACKCHAIN testnet (Sesi 12).
# Bind 127.0.0.1:8080 (lokal saja). Kunci validator val1 diekspor ke memori
# oleh faucet.py saat start; tidak pernah ditulis ke disk.
set -e
cd "$(dirname "$0")"
VENV=/home/hatch/workspace/blackchain/venvs/faucet/bin/python
if [ ! -x "$VENV" ]; then
  echo "venv tidak ditemukan: $VENV" >&2
  echo "Buat dulu: python3 -m venv ~/workspace/blackchain/venvs/faucet && <venv>/bin/pip install eth-account" >&2
  exit 1
fi
exec "$VENV" faucet.py
