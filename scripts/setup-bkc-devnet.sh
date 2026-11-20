#!/usr/bin/env bash
# BLACKCHAIN — setup devnet identitas BKC dari nol (Sesi 4, 2026-11-20).
# Chain: blackchain_20261120-1 | EVM chain ID 20261120 (0x1352900) | denom abkc.
# CATATAN: `keys add` mencetak mnemonic test SEKALI ke stdout (kunci devnet
# lokal tanpa nilai). Mnemonic itu TIDAK disimpan ke file/log mana pun.
# Jalankan: bash scripts/setup-bkc-devnet.sh
# Lalu start manual (lihat docs/06-evm-identity-bkc.md untuk perintah start).
set -euo pipefail
B="$HOME/workspace/blackchain/build/blackchaind-sdk54-bkc"
H="$HOME/workspace/blackchain/devnet-data-bkc/cosmos"
VENV="$HOME/workspace/.build-tmp/evmtest-venv/bin/python"

rm -rf "$H"
"$B" init blackchain-validator --chain-id blackchain_20261120-1 --home "$H" >/dev/null
"$B" keys add validator --keyring-backend test --home "$H" >/dev/null 2>&1 || true
# keys add mencetak mnemonic ke stdout di atas (diarahkan ke /dev/null hanya
# untuk pesan sukses; mnemonic tetap tampil sekali dari perintah itu sendiri
# bila keyring memintanya — itu perilaku CLI, bukan penyimpanan).

# Alamat ETH + bech32 dari pubkey validator (murni derivasi, tanpa kunci privat).
ETH_BECH32=$("$VENV" - "$H" <<'PYEOF'
import base64, json, subprocess, sys
home = sys.argv[1]
out = subprocess.check_output(['./blackchaind-sdk54-bkc', 'keys', 'show', 'validator',
                               '--keyring-backend', 'test', '--home', home, '--output', 'json'],
                              cwd='/home/hatch/workspace/blackchain/build')
d = json.loads(out)
pub = base64.b64decode(json.loads(d['pubkey'])['key'])
from eth_hash.auto import keccak
P = 0xfffffffffffffffffffffffffffffffffffffffffffffffffffffffefffffc2f
prefix, x = pub[0], int.from_bytes(pub[1:], 'big')
y = pow((pow(x, 3, P) + 7) % P, (P + 1) // 4, P)
if (y % 2 == 0) != (prefix == 0x02):
    y = P - y
eth = keccak(x.to_bytes(32, 'big') + y.to_bytes(32, 'big')).hex()[-40:]
CHARSET = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l'
def polymod(values):
    GEN = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3]
    chk = 1
    for v in values:
        b = chk >> 25
        chk = (chk & 0x1ffffff) << 5 ^ v
        for i in range(5):
            chk ^= GEN[i] if ((b >> i) & 1) else 0
    return chk
def hrp_expand(hrp):
    return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]
def convertbits(data, frombits, tobits, pad=True):
    acc, bits, ret = 0, 0, []
    maxv = (1 << tobits) - 1
    for value in data:
        acc = (acc << frombits) | value; bits += frombits
        while bits >= tobits:
            bits -= tobits; ret.append((acc >> bits) & maxv)
    if pad and bits:
        ret.append((acc << (tobits - bits)) & maxv)
    return ret
data = convertbits(list(bytes.fromhex(eth)), 8, 5)
values = hrp_expand('black') + data
pm = polymod(values + [0, 0, 0, 0, 0, 0]) ^ 1
cs = [(pm >> 5 * (5 - i)) & 31 for i in range(6)]
print('black1' + ''.join(CHARSET[d] for d in data + cs))
print('ETH=0x' + eth, file=sys.stderr)
PYEOF
)
echo "ETH bech32: $ETH_BECH32"
PUB_B64=$("$B" keys show validator --keyring-backend test --home "$H" --output json 2>/dev/null | "$VENV" -c "import json,sys; print(json.loads(json.load(sys.stdin)['pubkey'])['key'])")

"$B" genesis add-genesis-account validator 1000000000000000000000000abkc --keyring-backend test --home "$H" >/dev/null
"$B" genesis add-genesis-account "$ETH_BECH32" 1000000000000000000000000abkc --home "$H" >/dev/null

# Genesis: metadata BKC + akun auth ETH (ethsecp256k1) + parameter validator/testnet.
GEN="$H/config/genesis.json"
"$VENV" - "$GEN" "$ETH_BECH32" "$PUB_B64" <<'PYEOF'
import json, sys
p, eth_addr, pub_b64 = sys.argv[1], sys.argv[2], sys.argv[3]
g = json.load(open(p))
g['app_state']['bank']['denom_metadata'] = [{
    "description": "BLACKCHAIN native coin (EVM gas token)",
    "denom_units": [{"denom": "abkc", "exponent": 0, "aliases": []},
                    {"denom": "BKC", "exponent": 18, "aliases": []}],
    "base": "abkc", "display": "BKC", "name": "BLACKCHAIN", "symbol": "BKC"}]
for a in g['app_state']['auth']['accounts']:
    if a['address'] == eth_addr:
        a['pub_key'] = {"@type": "/cosmos.evm.crypto.v1.ethsecp256k1.PubKey", "key": pub_b64}
        a['account_number'] = "1"
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

"$B" genesis gentx validator 1000000000000000000000abkc --chain-id blackchain_20261120-1 --keyring-backend test --home "$H" >/dev/null
"$B" genesis collect-gentxs --home "$H" >/dev/null
"$B" genesis validate --home "$H"

# Config: mempool Krakatoa, port, [evm] chain ID.
python3 - <<PYEOF
p = '$H/config/config.toml'
s = open(p).read().replace('type = "flood"', 'type = "app"')
open(p, 'w').write(s)
p2 = '$H/config/app.toml'
a = open(p2).read()
a = a.replace('address = "tcp://localhost:1317"', 'address = "tcp://127.0.0.1:1328"')
a = a.replace('address = "localhost:9090"', 'address = "127.0.0.1:9102"')
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
print('config OK: mempool=app, api=1328, grpc=9102, evm-chain-id=20261120')
PYEOF
echo "SETUP SELESAI. Home: $H"
