#!/usr/bin/env bash
# BLACKCHAIN — restart semua node lokal setelah reboot VM (Sesi 9, F35).
# Menyalakan ulang dari home yang sudah ada (data di disk bertahan):
#   - devnet BKC (Jalur A): 1 validator, JSON-RPC 8555
#   - testnet rehearsal: 4 validator, JSON-RPC 8655/8665/8675/8685
#   - devnet fork Fase 1: 1 validator, JSON-RPC 8755
# Semua node listen 127.0.0.1 saja (tidak ada port publik).
# Penggunaan: ./repo/scripts/restart-all-nodes.sh
# Verifikasi: curl tiap port /status, lihat height + catching_up=false.
set -u
cd "$HOME/workspace/blackchain" || exit 1

BKC=./build/blackchaind-sdk54-bkc
PHASE1=./build/blackchaind-phase1

start_node() {
  local name="$1" bin="$2" home="$3" log="$4"; shift 4
  if pgrep -f "start --home $home" >/dev/null 2>&1; then
    echo "$name: SUDAH JALAN, lewati"
    return 0
  fi
  nohup "$bin" start --home "$home" --minimum-gas-prices 0abkc "$@" >> "$log" 2>&1 &
  echo "$name: start PID $! (log: $log)"
}

start_node "devnet-bkc" "$BKC" "$HOME/workspace/blackchain/devnet-data-bkc/cosmos" \
  devnet-data-bkc/cosmos-node5.log \
  --rpc.laddr tcp://127.0.0.1:26677 --p2p.laddr tcp://127.0.0.1:26676 \
  --grpc.address 127.0.0.1:9102 --rpc.pprof_laddr 127.0.0.1:6071 \
  --json-rpc.enable=true --json-rpc.address 127.0.0.1:8555 \
  --json-rpc.ws-address 127.0.0.1:8556
sleep 2

for i in 1 2 3 4; do
  case $i in
    1) RPC=26777; P2P=26776; GRPC=9202; PPROF=6171; EVM=8655; WS=8656;;
    2) RPC=26787; P2P=26786; GRPC=9203; PPROF=6172; EVM=8665; WS=8666;;
    3) RPC=26797; P2P=26796; GRPC=9204; PPROF=6173; EVM=8675; WS=8676;;
    4) RPC=26807; P2P=26806; GRPC=9205; PPROF=6174; EVM=8685; WS=8686;;
  esac
  start_node "val$i" "$BKC" "$HOME/workspace/blackchain/testnet-data/val$i" \
    "testnet-data/val$i-node.log" \
    --rpc.laddr "tcp://127.0.0.1:$RPC" --p2p.laddr "tcp://127.0.0.1:$P2P" \
    --grpc.address "127.0.0.1:$GRPC" --rpc.pprof_laddr "127.0.0.1:$PPROF" \
    --json-rpc.enable=true --json-rpc.address "127.0.0.1:$EVM" \
    --json-rpc.ws-address "127.0.0.1:$WS"
  sleep 2
done

start_node "fork-phase1" "$PHASE1" "$HOME/workspace/blackchain/phase1-data/cosmos" \
  phase1-data/cosmos-node.log \
  --rpc.laddr tcp://127.0.0.1:26877 --p2p.laddr tcp://127.0.0.1:26876 \
  --grpc.address 127.0.0.1:9302 --rpc.pprof_laddr 127.0.0.1:6271 \
  --json-rpc.enable=true --json-rpc.address 127.0.0.1:8755 \
  --json-rpc.ws-address 127.0.0.1:8756

echo "Menunggu 12 detik lalu memeriksa status..."
sleep 12
for p in 26677 26777 26787 26797 26807 26877; do
  printf "Comet %s: " "$p"
  curl -s -m 5 "http://127.0.0.1:$p/status" 2>/dev/null | python3 -c \
    "import sys,json; d=json.load(sys.stdin); s=d['result']['sync_info']; print('height', s['latest_block_height'], 'catching_up', s['catching_up'])" 2>/dev/null \
    || echo "TIDAK MENJAWAB"
done
