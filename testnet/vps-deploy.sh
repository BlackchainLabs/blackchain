#!/usr/bin/env bash
# =============================================================================
# BLACKCHAIN — Deploy Seed Node Publik Testnet di VPS (Sesi 11)
# -----------------------------------------------------------------------------
# Dijalankan DI VPS (bukan di VM lokal), sebagai user non-root dengan sudo.
#
#   ./vps-deploy.sh <IP-PUBLIK-VPS> [--dry-run] [--allow-local-build]
#
#   Contoh: ./vps-deploy.sh 203.0.113.10
#           ./vps-deploy.sh 203.0.113.10 --dry-run   # cek rencana saja,
#                                                     # tanpa efek samping
#           ./vps-deploy.sh 203.0.113.10 --allow-local-build
#               # binary hasil build sendiri di VPS (lihat chain/BUILD.md);
#               # cek sha256 binary dilewati, genesis tetap dicek.
#
# ARSITEKTUR (lihat docs/21-vps-seed-deployment.md):
# - VPS ini menjadi SEED NODE + FULL NODE PUBLIK, BUKAN validator.
#   Tidak ada kunci validator yang dipindah ke VPS ini — kunci validator
#   4 node rehearsal tetap di VM lokal dan TIDAK PERNAH keluar dari sana.
# - Rantai yang dipakai adalah rantai yang SUDAH BERJALAN (genesis
#   blackchain-testnet-genesis.json, chain-id blackchain_20261120-1,
#   height sudah ~500+). TIDAK ADA genesis baru.
# - Node lokal di VM ini TIDAK BISA di-dial dari internet (hanya
#   127.0.0.1). Arah koneksi: 4 validator lokal DIAL KELUAR ke VPS ini
#   (persistent_peers di tiap home val1..val4, lihat vps-runbook.md §4).
#   Karena itu persistent_peers seed ini KOSONG — seed tidak perlu
#   peer tetap; peer akan datang sendiri (validator lokal + validator
#   eksternal yang bergabung lewat seed ini).
# - Binary didapat dengan DUA cara (lihat vps-runbook.md §2):
#   (a) transfer via scp dari VM pengembang — dicek sha256; atau
#   (b) build dari source di VPS (repo/chain/, lihat chain/BUILD.md)
#       + flag --allow-local-build — cek sha256 binary dilewati karena
#       binary hasil build lokal selalu beda hash-nya.
#   Genesis SELALU dicek sha256-nya, apa pun cara perolehan binary.
#
# PORT (keputusan Sesi 11, sesuai docs/18 §5):
# - 26656/TCP (P2P) ........... SATU-SATUNYA port yang dibuka ke publik.
# - 26657 (RPC CometBFT) ...... TERTUTUP (bind 127.0.0.1 saja).
# - 8545/8546 (JSON-RPC/WS) ... TERTUTUP (bind 127.0.0.1 saja).
#   JSON-RPC tetap di-enable agar operator bisa query dari dalam VPS,
#   tetapi TIDAK diekspos ke internet. RPC publik read-only lewat
#   reverse proxy + rate limit adalah KEPUTUSAN PEMILIK yang terpisah
#   (belum diputuskan) — JANGAN buka port ini diam-diam; lihat
#   docs/21 §4.
# - 9090 (gRPC), 1317 (REST) .. TERTUTUP (bind 127.0.0.1 / disable).
# - 22/TCP (SSH) .............. dibuka agar akses admin tetap jalan;
#   idealnya dibatasi ke IP admin bila VPS mendukung (lihat catatan
#   di bawah pada bagian ufw).
#
# KEAMANAN:
# - `blackchaind init` membuat priv_validator_key.json di home node.
#   Untuk seed node file ini INERT (node tidak ada di validator set),
#   tetapi JANGAN PERNAH dibagikan, disalin keluar VPS, atau dipakai
#   untuk membuat validator. Identitas P2P seed adalah node_key.json.
# - Jangan pernah meminta/menyimpan seed phrase atau private key
#   siapa pun di script/log mana pun.
# =============================================================================
set -euo pipefail

CHAIN_ID="blackchain_20261120-1"
MONIKER="blackchain-seed-1"
HOME_DIR="${HOME}/.blackchain"
DEPLOY_DIR="${HOME}/blackchain-deploy"
BIN_SRC="${DEPLOY_DIR}/blackchaind"
GENESIS_SRC="${DEPLOY_DIR}/blackchain-testnet-genesis.json"
BIN_DST="/usr/local/bin/blackchaind"
SERVICE_NAME="blackchaind-seed"

# SHA-256 terverifikasi di VM lokal 2026-11-21 (Sesi 11).
# Binary Jalur A: build/blackchaind-sdk54-bkc (SDK v0.54.5 + Cosmos EVM v0.7.4).
# Genesis: repo/testnet/blackchain-testnet-genesis.json (4 gentx, 30.080.000 BKC).
BIN_SHA256="37766ab8672c0d3cfdb6a6640bbb073b6d42abba9e79b7619d3424ec3a6b9f06"
GENESIS_SHA256="0fbd6b09664011e2ddad0866e58243ed5c2180421636776a34f1a0ac8c152431"

DRY_RUN=0
ALLOW_LOCAL_BUILD=0
VPS_IP=""
DEPLOY_USER="$(id -un)"

usage() {
  echo "Pakai: $0 <IP-PUBLIK-VPS> [--dry-run] [--allow-local-build]"
  echo "Contoh: $0 203.0.113.10"
  echo "        $0 203.0.113.10 --allow-local-build  # binary hasil build sendiri di VPS"
  exit 1
}

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --allow-local-build) ALLOW_LOCAL_BUILD=1 ;;
    --help|-h) usage ;;
    *) if [ -z "$VPS_IP" ]; then VPS_IP="$arg"; else echo "Argumen tak dikenal: $arg"; usage; fi ;;
  esac
done

[ -n "$VPS_IP" ] || usage

# Validasi format IPv4 sederhana (bukan validasi kepemilikan — IP harus
# sudah dikonfirmasi pemilik; jangan tebak IP).
if ! [[ "$VPS_IP" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "ERROR: '$VPS_IP' bukan alamat IPv4. Isi IP publik VPS yang sebenarnya."
  exit 1
fi

say()  { echo "[vps-deploy] $*"; }
die()  { echo "[vps-deploy] ERROR: $*" >&2; exit 1; }

if [ "$DRY_RUN" = "1" ]; then
  say "DRY-RUN — tidak ada perubahan yang dibuat. Rencana:"
  say "  VPS IP ..........: $VPS_IP"
  say "  User ............: ${DEPLOY_USER} (non-root, sudo dipakai untuk ufw + systemd)"
  say "  Binary ..........: $BIN_SRC -> $BIN_DST (cek sha256 $BIN_SHA256)"
  if [ "$ALLOW_LOCAL_BUILD" = "1" ]; then
    say "  Cek sha256 binary : DILEWATI (--allow-local-build, binary build lokal)"
  fi
  say "  Genesis .........: $GENESIS_SRC (cek sha256 $GENESIS_SHA256)"
  say "  Home node .......: $HOME_DIR (init moniker $MONIKER, chain $CHAIN_ID)"
  say "  P2P .............: 0.0.0.0:26656, external_address $VPS_IP:26656"
  say "  RPC/EVM/gRPC ....: bind 127.0.0.1 saja (26657 / 8545 / 8546 / 9090)"
  say "  Firewall ........: ufw allow 22, 26656; deny 26657, 8545, 8546, 9090, 1317"
  say "  Service .........: systemd $SERVICE_NAME (restart always)"
  [ -f "$BIN_SRC" ]     || die "binary belum ada di $BIN_SRC — transfer dulu via scp (runbook §2)."
  [ -f "$GENESIS_SRC" ] || die "genesis belum ada di $GENESIS_SRC — transfer dulu via scp (runbook §2)."
  say "DRY-RUN OK: file transfer sudah lengkap, siap deploy."
  exit 0
fi

# --- 0. Prasyarat -----------------------------------------------------------
[ "$EUID" -ne 0 ] || die "Jangan jalankan script ini sebagai root. Pakai user non-root dengan sudo."
sudo -n true 2>/dev/null || die "sudo tanpa password tidak tersedia / sudo gagal. Pastikan user ${DEPLOY_USER} ada di grup sudo."
for cmd in curl jq ufw systemctl python3; do
  command -v "$cmd" >/dev/null 2>&1 || die "dependensi hilang: $cmd. Instal dulu (mis. sudo apt install -y $cmd)."
done
if [ -f /etc/os-release ]; then
  # shellcheck disable=SC1091
  . /etc/os-release
  say "OS: ${PRETTY_NAME:-$ID $VERSION_ID}"
  case "${ID:-}" in
    ubuntu) say "Ubuntu terdeteksi (yang didukung: 22.04 / 24.04)." ;;
    debian) say "PERINGATAN: Debian — belum diuji untuk binary ini, lanjut dengan hati-hati." ;;
    *)      say "PERINGATAN: distro ${ID:-?} belum diuji untuk binary ini, lanjut dengan hati-hati." ;;
  esac
fi

# --- 1. Verifikasi file transfer (binary + genesis) --------------------------
[ -f "$BIN_SRC" ]     || die "binary belum ada di $BIN_SRC — transfer dulu via scp atau build dari source (runbook §2)."
[ -f "$GENESIS_SRC" ] || die "genesis belum ada di $GENESIS_SRC — transfer dulu via scp (runbook §2)."
say "Memverifikasi sha256 binary + genesis ..."
if [ "$ALLOW_LOCAL_BUILD" = "1" ]; then
  # Binary hasil build lokal di VPS SELALU beda hash-nya dari binary hasil
  # build di VM pengembang (metadata build: path, versi Go, ldflags) —
  # dibuktikan 2026-11-21: build ulang dari source yang sama menghasilkan
  # sha256 48088178... vs 37766ab8... — jadi cek sha256 binary dilewati.
  # Genesis tetap dicek: genesis adalah konsensus, tidak boleh beda.
  say "ALLOW-LOCAL-BUILD: cek sha256 binary DILEWATI (binary build lokal)."
  echo "${GENESIS_SHA256}  ${GENESIS_SRC}" | sha256sum -c - || die "sha256 GENESIS TIDAK COCOK — jangan lanjut, unduh ulang dari GitHub."
  say "sha256 genesis cocok."
else
  echo "${BIN_SHA256}  ${BIN_SRC}" | sha256sum -c - || die "sha256 BINARY TIDAK COCOK — jangan lanjut, transfer ulang dari VM."
  echo "${GENESIS_SHA256}  ${GENESIS_SRC}" | sha256sum -c - || die "sha256 GENESIS TIDAK COCOK — jangan lanjut, transfer ulang dari VM."
  say "sha256 cocok."
fi

# --- 2. Instal binary ---------------------------------------------------------
say "Menginstal binary ke $BIN_DST ..."
sudo install -m 0755 "$BIN_SRC" "$BIN_DST"
"$BIN_DST" version 2>/dev/null | head -3 || say "(perintah version tidak mencetak output — lanjut; verifikasi akhir di §6 yang menentukan.)"

# --- 3. Init seed node ---------------------------------------------------------
if [ -d "$HOME_DIR" ]; then
  die "$HOME_DIR sudah ada. Hapus manual bila yakin ingin init ulang (rm -rf $HOME_DIR), lalu jalankan lagi. JANGAN hapus bila node sudah sinkron."
fi
say "Init node: moniker=$MONIKER chain-id=$CHAIN_ID ..."
"$BIN_DST" init "$MONIKER" --chain-id "$CHAIN_ID" --home "$HOME_DIR"
say "Menyalin genesis testnet ..."
cp "$GENESIS_SRC" "$HOME_DIR/config/genesis.json"
"$BIN_DST" genesis validate --home "$HOME_DIR"
say "Genesis VALID."

# --- 4. Konfigurasi config.toml + app.toml -------------------------------------
# Editan dilakukan dengan python3 (parser per-baris, sadar section) agar
# tidak salah sasaran — config.toml punya DUA kunci `laddr` ([rpc] dan
# [p2p]) dan regex `.*$` yang serakah akan memotong file sampai akhir.
say "Mengonfigurasi config.toml ..."
python3 - "$HOME_DIR/config/config.toml" "$VPS_IP" <<'PYEOF'
import sys
path, vps_ip = sys.argv[1], sys.argv[2]

def edit_toml(path, edits):
    lines = open(path).read().splitlines(keepends=True)
    out, section, seen = [], None, set()
    for line in lines:
        s = line.strip()
        if s.startswith('[') and s.endswith(']'):
            section = s[1:-1].strip()
            out.append(line)
            continue
        if section in edits and not s.startswith('#') and '=' in line:
            key = line.split('=', 1)[0].strip()
            if key in edits[section]:
                indent = line[:len(line) - len(line.lstrip())]
                out.append(f"{indent}{key} = {edits[section][key]}\n")
                seen.add((section, key))
                continue
        out.append(line)
    missing = [(sec, k) for sec, d in edits.items() for k in d
               if (sec, k) not in seen]
    if missing:
        raise SystemExit(f'KUNCI TIDAK DITEMUKAN di {path}: {missing}')
    open(path, 'w').write(''.join(out))

edit_toml(path, {
    # RPC CometBFT: localhost saja — TIDAK dibuka ke publik.
    'rpc': {'laddr': '"tcp://127.0.0.1:26657"'},
    'p2p': {
        # P2P: dengarkan semua interface (publik), umumkan IP publik VPS.
        'laddr': '"tcp://0.0.0.0:26656"',
        'external_address': f'"{vps_ip}:26656"',
        # Seed TIDAK butuh peer tetap: peer (validator lokal + eksternal)
        # yang dial ke seed.
        'persistent_peers': '""',
        'seeds': '""',
        # Mode seed: node merespons peer exchange dan TIDAK ikut konsensus.
        'seed_mode': 'true',
        'pex': 'true',
        # Aturan alamat KETAT (publik): kebalikan dari rehearsal lokal yang
        # memakai allow_duplicate_ip=true + addr_book_strict=false
        # karena 127.0.0.1.
        'addr_book_strict': 'true',
        'allow_duplicate_ip': 'false',
    },
})
print('config.toml OK: rpc 127.0.0.1:26657, p2p 0.0.0.0:26656, '
      f'external_address {vps_ip}:26656, seed_mode=true, addr_book_strict=true')
PYEOF

# gRPC + REST API juga localhost/disable — lihat keputusan port di header.
say "Mengonfigurasi app.toml (gRPC localhost, REST API nonaktif) ..."
python3 - "$HOME_DIR/config/app.toml" <<'PYEOF'
import sys
path = sys.argv[1]

def edit_toml(path, edits):
    lines = open(path).read().splitlines(keepends=True)
    out, section, seen = [], None, set()
    for line in lines:
        s = line.strip()
        if s.startswith('[') and s.endswith(']'):
            section = s[1:-1].strip()
            out.append(line)
            continue
        if section in edits and not s.startswith('#') and '=' in line:
            key = line.split('=', 1)[0].strip()
            if key in edits[section]:
                indent = line[:len(line) - len(line.lstrip())]
                out.append(f"{indent}{key} = {edits[section][key]}\n")
                seen.add((section, key))
                continue
        out.append(line)
    missing = [(sec, k) for sec, d in edits.items() for k in d
               if (sec, k) not in seen]
    if missing:
        raise SystemExit(f'KUNCI TIDAK DITEMUKAN di {path}: {missing}')
    open(path, 'w').write(''.join(out))

edit_toml(path, {
    'grpc': {'address': '"127.0.0.1:9090"'},
    'api': {'enable': 'false'},
})
print('app.toml OK: grpc 127.0.0.1:9090, REST API enable=false')
PYEOF

# --- 5. Systemd service --------------------------------------------------------
say "Membuat systemd service $SERVICE_NAME ..."
sudo tee "/etc/systemd/system/${SERVICE_NAME}.service" >/dev/null <<EOF
[Unit]
Description=BLACKCHAIN testnet seed node (blackchain_20261120-1)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${DEPLOY_USER}
Group=${DEPLOY_USER}
WorkingDirectory=${HOME}
ExecStart=${BIN_DST} start --home ${HOME_DIR} \\
  --minimum-gas-prices 0abkc \\
  --log_level *:info \\
  --rpc.laddr tcp://127.0.0.1:26657 \\
  --p2p.laddr tcp://0.0.0.0:26656 \\
  --grpc.address 127.0.0.1:9090 \\
  --rpc.pprof_laddr 127.0.0.1:6171 \\
  --json-rpc.enable=true \\
  --json-rpc.address 127.0.0.1:8545 \\
  --json-rpc.ws-address 127.0.0.1:8546
Restart=always
RestartSec=10
LimitNOFILE=65535
# Seed node BUKAN validator: tidak ada kunci validator yang dipakai di sini.
# priv_validator_key.json yang dibuat `init` bersifat inert — JANGAN dibagikan.

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"

# --- 6. Firewall (ufw) ----------------------------------------------------------
# Urutan penting: allow SSH + P2P DULU, baru enable, agar tidak terkunci.
say "Mengonfigurasi ufw (allow 22 + 26656; deny 26657/8545/8546/9090/1317) ..."
sudo ufw allow 22/tcp comment 'SSH admin'
sudo ufw allow 26656/tcp comment 'BLACKCHAIN P2P testnet'
sudo ufw deny 26657/tcp comment 'BLACKCHAIN RPC - closed'
sudo ufw deny 8545/tcp comment 'BLACKCHAIN JSON-RPC - closed'
sudo ufw deny 8546/tcp comment 'BLACKCHAIN JSON-RPC WS - closed'
sudo ufw deny 9090/tcp comment 'BLACKCHAIN gRPC - closed'
sudo ufw deny 1317/tcp comment 'BLACKCHAIN REST - closed'
# CATATAN: bila VPS ini hanya boleh di-SSH dari IP admin tertentu, ganti
# aturan 22 di atas dengan: sudo ufw delete allow 22/tcp &&
# sudo ufw allow from <IP-ADMIN> to any port 22 proto tcp
# (keputusan operator; tidak diubah otomatis oleh script ini).
sudo ufw --force enable
sudo ufw status numbered

# --- 7. Start + verifikasi --------------------------------------------------------
say "Menyalakan service $SERVICE_NAME ..."
sudo systemctl start "$SERVICE_NAME"
sleep 15
sudo systemctl status "$SERVICE_NAME" --no-pager | head -20

SEED_NODE_ID="$("$BIN_DST" tendermint show-node-id --home "$HOME_DIR")"
say "Node ID seed: $SEED_NODE_ID"
say "Alamat seed publik: ${SEED_NODE_ID}@${VPS_IP}:26656"
say "CATAT alamat di atas — inilah yang dimasukkan ke repo/testnet/seeds.md"
say "dan ke persistent_peers 4 validator lokal (vps-runbook.md §4)."
echo ""
say "Verifikasi (dari DALAM VPS):"
curl -s http://127.0.0.1:26657/status | jq '{chain_id: .result.node_info.network, height: .result.sync_info.latest_block_height, catching_up: .result.sync_info.catching_up, peers: (.result.node_info.other // {})}'
curl -s -X POST http://127.0.0.1:8545 -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1}' | jq .
echo ""
say "SELESAI. Langkah berikut ada di vps-runbook.md §4–§5:"
say "  1) Isi alamat seed di atas ke repo/testnet/seeds.md"
say "  2) Hubungkan 4 validator lokal (dial keluar ke seed ini)"
say "  3) Verifikasi seed dari luar + umumkan bila semua hijau"
