#!/usr/bin/env bash
# BLACKCHAIN — setup testnet rehearsal 4 validator (Sesi 8, 2026-11-20).
# 4 validator (bukan 3): dengan 3 validator setara, 2/3 daya = tepat 2/3 dan
# TIDAK > 2/3, sehingga 1 validator mati = chain halt (F33). Dengan 4
# validator, 3/4 = 75% > 2/3 sehingga 1 validator mati tetap liveness.
# Chain: blackchain_20261120-1 | EVM chain ID 20261120 (0x1352900) | denom abkc.
# Binary: build/blackchaind-sdk54-bkc (Cosmos SDK v0.54.5 + Cosmos EVM v0.7.4).
# Homes: workspace/blackchain/testnet-data/val{1,2,3,4} (semua 127.0.0.1).
# CATATAN: `keys add` mencetak mnemonic test SEKALI ke stdout (kunci testnet
# lokal tanpa nilai). Mnemonic itu TIDAK disimpan ke file/log mana pun.
# Alokasi genesis (testnet, tanpa nilai):
#   - tiap validator: 10.000 BKC (self-stake gentx 1.000 BKC)
#   - val1 (operator rehearsal) tambahan: 20.000.000 tBKC pool subsidi
#     testnet (pagu docs/06 §5) + 10.000.000 tBKC pool faucet — dipegang
#     alamat operator SELAMA rehearsal; SEBELUM pembukaan publik dana ini
#     WAJIB dipindah ke community pool / multisig lewat gov. Bukan alokasi
#     tim/mainnet (itu urusan mainnet, tidak ada di genesis ini).
# Jalankan: bash scripts/setup-testnet-4val.sh
# Lalu start manual (lihat docs/17-testnet-multivalidator.md).
set -euo pipefail
B="$HOME/workspace/blackchain/build/blackchaind-sdk54-bkc"
T="$HOME/workspace/blackchain/testnet-data"
VENV="$HOME/workspace/.build-tmp/evmtest-venv/bin/python"
PY="$HOME/workspace/blackchain/repo/scripts/eth_bech32.py"
CHAIN="blackchain_20261120-1"

# Saldo genesis (abkc; 1 BKC = 10^18 abkc)
VAL_BALANCE="10000000000000000000000"        # 10.000 BKC
VAL1_BALANCE="30010000000000000000000000"    # 30.010.000 BKC (10.000 + 20jt subsidi + 10jt faucet)
GENTX="1000000000000000000000"               # 1.000 BKC self-stake

rm -rf "$T"
mkdir -p "$T"

declare -A ETH BECH PUB STAKE
for i in 1 2 3 4; do
  H="$T/val$i"
  "$B" init "blackchain-testnet-val$i" --chain-id "$CHAIN" --home "$H" >/dev/null
  "$B" keys add validator --keyring-backend test --home "$H" >/dev/null 2>&1 || true
  BECH[$i]=$("$VENV" "$PY" "$H" validator 2>"$T/val$i-eth.txt")
  ETH[$i]=$(cat "$T/val$i-eth.txt")
  PUB[$i]=$("$B" keys show validator --keyring-backend test --home "$H" --output json 2>/dev/null \
    | "$VENV" -c "import json,sys; print(json.loads(json.load(sys.stdin)['pubkey'])['key'])")
  STAKE[$i]=$("$B" keys show validator --keyring-backend test --home "$H" --output json 2>/dev/null \
    | "$VENV" -c "import json,sys; print(json.load(sys.stdin)['address'])")
  echo "val$i staking: ${STAKE[$i]}  bech32: ${BECH[$i]}  ${ETH[$i]}"
  echo "${BECH[$i]}" > "$T/val$i-bech32.txt"
  echo "${STAKE[$i]}" > "$T/val$i-staking.txt"
done

# --- Genesis bersama: dibangun di home val1, lalu disalin ke val2/val3. ---
H1="$T/val1"
if [ "${VAL1_BALANCE}" != "30010000000000000000000000" ]; then echo "FATAL: VAL1 balance salah"; exit 1; fi
# Alamat staking (secp256k1, untuk gentx) + alamat ETH (ethsecp256k1, untuk EVM)
# masing-masing didanai; val1 staking memegang tambahan pool subsidi + faucet.
"$B" genesis add-genesis-account "${STAKE[1]}" "$VAL1_BALANCE"abkc --home "$H1" >/dev/null
"$B" genesis add-genesis-account "${BECH[1]}" "$VAL_BALANCE"abkc --home "$H1" >/dev/null
"$B" genesis add-genesis-account "${STAKE[2]}" "$VAL_BALANCE"abkc --home "$H1" >/dev/null
"$B" genesis add-genesis-account "${BECH[2]}" "$VAL_BALANCE"abkc --home "$H1" >/dev/null
"$B" genesis add-genesis-account "${STAKE[3]}" "$VAL_BALANCE"abkc --home "$H1" >/dev/null
"$B" genesis add-genesis-account "${BECH[3]}" "$VAL_BALANCE"abkc --home "$H1" >/dev/null
"$B" genesis add-genesis-account "${STAKE[4]}" "$VAL_BALANCE"abkc --home "$H1" >/dev/null
"$B" genesis add-genesis-account "${BECH[4]}" "$VAL_BALANCE"abkc --home "$H1" >/dev/null

# Patch genesis: denom metadata, pubkey ethsecp256k1 tiap validator, parameter
# validator/testnet (sama seperti Sesi 4, docs/06).
GEN="$H1/config/genesis.json"
"$VENV" - "$GEN" "${BECH[1]}" "${PUB[1]}" "${BECH[2]}" "${PUB[2]}" "${BECH[3]}" "${PUB[3]}" "${BECH[4]}" "${PUB[4]}" <<'PYEOF'
import json, sys
p = sys.argv[1]
pairs = [(sys.argv[2], sys.argv[3]), (sys.argv[4], sys.argv[5]), (sys.argv[6], sys.argv[7]), (sys.argv[8], sys.argv[9])]
g = json.load(open(p))
g['app_state']['bank']['denom_metadata'] = [{
    "description": "BLACKCHAIN native coin (EVM gas token)",
    "denom_units": [{"denom": "abkc", "exponent": 0, "aliases": []},
                    {"denom": "BKC", "exponent": 18, "aliases": []}],
    "base": "abkc", "display": "BKC", "name": "BLACKCHAIN", "symbol": "BKC"}]
for addr, pub_b64 in pairs:
    for a in g['app_state']['auth']['accounts']:
        if a['address'] == addr:
            a['pub_key'] = {"@type": "/cosmos.evm.crypto.v1.ethsecp256k1.PubKey", "key": pub_b64}
st = g['app_state']['staking']['params']
st['max_validators'] = 100
st['min_commission_rate'] = "0.050000000000000000"
st['unbonding_time'] = "1814400s"
sl = g['app_state']['slashing']['params']
sl['signed_blocks_window'] = "100"
sl['min_signed_per_window'] = "0.500000000000000000"
sl['downtime_jail_duration'] = "600s"
sl['slash_fraction_double_sign'] = "0.050000000000000000"
sl['slash_fraction_downtime'] = "0.010000000000000000"
mi = g['app_state']['mint']
mi['minter']['inflation'] = "0.000000000000000000"
mi['minter']['annual_provisions'] = "0.000000000000000000"
mi['params']['inflation_rate_change'] = "0.000000000000000000"
mi['params']['inflation_max'] = "0.000000000000000000"
mi['params']['inflation_min'] = "0.000000000000000000"
mi['params']['max_supply'] = "1000000000000000000000000000"
mi['params']['blocks_per_year'] = "6307200"
gv = g['app_state']['gov']['params']
gv['min_deposit'] = [{"denom": "abkc", "amount": "10000000000000000000"}]
gv['expedited_min_deposit'] = [{"denom": "abkc", "amount": "50000000000000000000"}]
json.dump(g, open(p, 'w'), indent=2)
print('genesis params OK')
PYEOF

# --- Gentx tiap validator, lalu collect di val1. ---
for i in 1 2 3 4; do
  H="$T/val$i"
  # Salin genesis (dengan akun) ke home validator ini SEBELUM gentx, supaya
  # gentx memvalidasi saldo akun validator tersebut (val1 sudah memegang
  # genesis sumber, jadi lewati penyalinan untuk i=1).
  if [ "$i" != "1" ]; then cp "$GEN" "$H/config/genesis.json"; fi
  "$B" genesis gentx validator "$GENTX"abkc --chain-id "$CHAIN" --keyring-backend test --home "$H" >/dev/null
  echo "val$i gentx OK"
done
cp "$T"/val{2,3,4}/config/gentx/*.json "$H1/config/gentx/" 2>/dev/null || true
"$B" genesis collect-gentxs --home "$H1" >/dev/null
"$B" genesis validate --home "$H1"

# Salin genesis final (dengan 4 gentx) ke val2/val3/val4.
cp "$GEN" "$T/val2/config/genesis.json"
cp "$GEN" "$T/val3/config/genesis.json"
cp "$GEN" "$T/val4/config/genesis.json"

# --- Config per node: mempool Krakatoa, port, persistent_peers, [evm]. ---
ID1=$("$B" tendermint show-node-id --home "$T/val1")
ID2=$("$B" tendermint show-node-id --home "$T/val2")
ID3=$("$B" tendermint show-node-id --home "$T/val3")
ID4=$("$B" tendermint show-node-id --home "$T/val4")
echo "$ID1" > "$T/val1-node-id.txt"; echo "$ID2" > "$T/val2-node-id.txt"; echo "$ID3" > "$T/val3-node-id.txt"; echo "$ID4" > "$T/val4-node-id.txt"

python3 - "$T" "$ID1" "$ID2" "$ID3" "$ID4" <<'PYEOF'
import sys
T, ids = sys.argv[1], sys.argv[2:6]
ports = {
    1: {"rpc": 26777, "p2p": 26776, "grpc": 9202, "rest": 1338, "pprof": 6171},
    2: {"rpc": 26787, "p2p": 26786, "grpc": 9203, "rest": 1339, "pprof": 6172},
    3: {"rpc": 26797, "p2p": 26796, "grpc": 9204, "rest": 1340, "pprof": 6173},
    4: {"rpc": 26807, "p2p": 26806, "grpc": 9205, "rest": 1341, "pprof": 6174},
}
for i in (1, 2, 3, 4):
    h = f"{T}/val{i}"
    peers = ",".join(f"{ids[j-1]}@127.0.0.1:{ports[j]['p2p']}" for j in (1, 2, 3, 4) if j != i)
    p = f"{h}/config/config.toml"
    s = open(p).read()
    s = s.replace('type = "flood"', 'type = "app"')
    # Rehearsal lokal: ketiga validator di 127.0.0.1 (satu IP). Tanpa ini,
    # switch CometBFT menolak koneksi kedua dari IP yang sama (F32, Sesi 8)
    # dan konsensus macet di height 1. Node PUBLIK (IP routable berbeda)
    # memakai default (allow_duplicate_ip=false, addr_book_strict=true).
    s = s.replace('allow_duplicate_ip = false', 'allow_duplicate_ip = true')
    s = s.replace('addr_book_strict = true', 'addr_book_strict = false')
    s = s.replace('laddr = "tcp://127.0.0.1:26657"',
                  f'laddr = "tcp://127.0.0.1:{ports[i]["rpc"]}"')
    s = s.replace('laddr = "tcp://0.0.0.0:26656"',
                  f'laddr = "tcp://127.0.0.1:{ports[i]["p2p"]}"')
    s = s.replace('pprof_laddr = "localhost:6060"',
                  f'pprof_laddr = "127.0.0.1:{ports[i]["pprof"]}"')
    # persistent_peers: ganti nilai kosong/default dengan peer dua validator lain.
    import re
    s = re.sub(r'persistent_peers = "[^"]*"', f'persistent_peers = "{peers}"', s, count=1)
    open(p, 'w').write(s)
    p2 = f"{h}/config/app.toml"
    a = open(p2).read()
    a = a.replace('address = "tcp://localhost:1317"',
                  f'address = "tcp://127.0.0.1:{ports[i]["rest"]}"')
    a = a.replace('address = "localhost:9090"',
                  f'address = "127.0.0.1:{ports[i]["grpc"]}"')
    a += '''
###############################################################################
###                 EVM Configuration (BLACKCHAIN)                          ###
###############################################################################
[evm]
tracer = ""
max-tx-gas-wanted = 0
cache-preimage = false
# EIP-155 replay-protection chain ID — MUST match app.evmChainID (20261120).
evm-chain-id = 20261120
min-tip = 0
geth-metrics-address = "127.0.0.1:8100"
'''
    open(p2, 'w').write(a)
    print(f"val{i} config OK: rpc={ports[i]['rpc']} p2p={ports[i]['p2p']} peers={peers}")
PYEOF

echo "SETUP SELESAI. Homes: $T/val{1,2,3,4}"
echo "Start tiap node (contoh val1):"
echo "  $B start --home $T/val1 --minimum-gas-prices 0abkc --rpc.laddr tcp://127.0.0.1:26777 --p2p.laddr tcp://127.0.0.1:26776 --grpc.address 127.0.0.1:9202 --rpc.pprof_laddr 127.0.0.1:6171 --json-rpc.enable=true --json-rpc.address 127.0.0.1:8655 --json-rpc.ws-address 127.0.0.1:8656"
