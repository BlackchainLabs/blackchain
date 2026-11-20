#!/usr/bin/env python3
"""BLACKCHAIN Testnet Faucet v0.1 (Sesi 12) — server minimal yang BENAR-BENAR JALAN.

Melayani klaim 100 tBKC per alamat per 24 jam melawan rehearsal testnet
lokal (EVM JSON-RPC val1 127.0.0.1:8655, chain ID 20261120).

DANA FAUCET — FAKTA:
- Pengirim = alamat ETH validator val1 0x7C54D93649524Ad774125a9e8E03B1BC1043238c
  (kunci "validator" di testnet-data/val1, keyring test — kunci testnet rehearsal,
  tanpa nilai). Saldo cair saat dibangun: ~9.999,9999 BKC.
- Pool faucet 10.000.000 tBKC di genesis berstatus STAKED (bonded), BUKAN cair —
  tidak bisa dipakai faucet tanpa unbonding 21 hari / keputusan pemilik.
  Kapasitas efektif dari dana cair: ~99 klaim @100 tBKC.
- Private key diekspor IN-MEMORY saat start via `blackchaind keys export`
  (pola yang sama seperti scripts/testnet-transfer-test.py Sesi 8) dan TIDAK
  PERNAH ditulis ke file/log/laporan.

ANTI-SYBIL (jujur): TIDAK ada hCaptcha — butuh layanan eksternal + site key
(keputusan pemilik, docs/13 A.3). Yang dipakai: proof-of-work ringan
(sha256 harus diawali "0000"), cooldown alamat 24 jam, rate limit 5 klaim
per IP per hari, batas harian global 1.000.000 tBKC (di atas saldo cair).

HANYA stdlib + eth_account. Bind 127.0.0.1 (lokal saja — ekspos publik
butuh reverse proxy + keputusan pemilik).

Penggunaan:
  FAUCET_PORT=8080 ./start.sh        # atau: <venv>/bin/python faucet.py
  curl localhost:8080/api/status
"""
import hashlib
import json
import os
import re
import secrets
import subprocess
import threading
import time
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from eth_account import Account

BIN = "/home/hatch/workspace/blackchain/build/blackchaind-sdk54-bkc"
VAL1_HOME = os.environ.get(
    "FAUCET_HOME", "/home/hatch/workspace/blackchain/testnet-data/val1")
RPC_URL = os.environ.get("FAUCET_RPC", "http://127.0.0.1:8655")
CHAIN_ID = int(os.environ.get("FAUCET_CHAIN_ID", "20261120"))
PORT = int(os.environ.get("FAUCET_PORT", "8080"))
AMOUNT_WEI = 100 * 10**18          # 100 tBKC
COOLDOWN_S = 24 * 3600             # 24 jam per alamat
IP_DAILY_MAX = 5                   # klaim per IP per hari
GLOBAL_DAILY_CAP_WEI = 1_000_000 * 10**18
POW_PREFIX = "0000"                # sha256 hex diawali 4 nol (~65 ribu hash)
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
CLAIMS_FILE = os.path.join(DATA_DIR, "claims.json")
LOG_FILE = os.path.join(DATA_DIR, "claims.log")

ADDR_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")

# --- state (in-memory + persist ke disk) ---
_lock = threading.RLock()
_claims = {}        # addr_lower -> {"last_claim": ts, "tx_hash": str, "count": int}
_ip_claims = {}     # sha256(ip) -> [ts, ...]
_challenges = {}    # challenge -> {"address": addr, "issued": ts}
_sender = None


def rpc_call(method, params=None):
    body = json.dumps(
        {"jsonrpc": "2.0", "method": method, "params": params or [], "id": 1}
    ).encode()
    req = urllib.request.Request(
        RPC_URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        out = json.load(r)
    if "error" in out:
        raise RuntimeError(f"{method} -> {out['error']}")
    return out["result"]


def load_state():
    global _claims, _ip_claims
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(CLAIMS_FILE):
        with open(CLAIMS_FILE) as f:
            data = json.load(f)
        _claims = data.get("claims", {})
        _ip_claims = data.get("ip_claims", {})


def save_state():
    tmp = CLAIMS_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump({"claims": _claims, "ip_claims": _ip_claims}, f, indent=2)
    os.replace(tmp, CLAIMS_FILE)


def log_claim(entry):
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def load_sender():
    """Ekspor kunci validator val1 ke memori saja (pola Sesi 8)."""
    global _sender
    pk_hex = subprocess.check_output(
        [BIN, "keys", "export", "validator", "--keyring-backend", "test",
         "--home", VAL1_HOME, "--unarmored-hex", "--unsafe", "-y"],
        stderr=subprocess.DEVNULL).decode().strip()
    _sender = Account.from_key(pk_hex)
    # pk_hex sengaja TIDAK disimpan di variabel lain / log.
    return _sender


def verify_pow(address, challenge, nonce):
    ch = _challenges.get(challenge)
    if not ch or ch["address"] != address.lower():
        return False, "challenge tidak valid / kedaluwarsa"
    if time.time() - ch["issued"] > 600:
        del _challenges[challenge]
        return False, "challenge kedaluwarsa (>10 menit)"
    digest = hashlib.sha256(
        f"{address.lower()}:{challenge}:{nonce}".encode()).hexdigest()
    if not digest.startswith(POW_PREFIX):
        return False, "proof-of-work tidak valid"
    del _challenges[challenge]
    return True, ""


def do_claim(address, ip):
    """Kirim 100 tBKC. Harus dipanggil dengan _lock dipegang. Kembalikan dict."""
    now = int(time.time())
    addr = address.lower()
    ip_hash = hashlib.sha256(ip.encode()).hexdigest()

    prev = _claims.get(addr)
    if prev and now - prev["last_claim"] < COOLDOWN_S:
        wait_h = (COOLDOWN_S - (now - prev["last_claim"])) / 3600
        return {"ok": False, "error": "cooldown",
                "message": f"Alamat ini sudah klaim. Coba lagi dalam {wait_h:.1f} jam.",
                "next_claim_at": prev["last_claim"] + COOLDOWN_S}

    today = [t for t in _ip_claims.get(ip_hash, [])
             if now - t < COOLDOWN_S]
    if len(today) >= IP_DAILY_MAX:
        return {"ok": False, "error": "ip_limit",
                "message": f"IP ini sudah mencapai {IP_DAILY_MAX} klaim/24 jam."}

    day_start = now - (now % 86400)
    spent_today = sum(
        AMOUNT_WEI for c in _claims.values()
        if c["last_claim"] >= day_start)
    if spent_today + AMOUNT_WEI > GLOBAL_DAILY_CAP_WEI:
        return {"ok": False, "error": "global_cap",
                "message": "Batas harian global faucet tercapai."}

    balance = int(rpc_call("eth_getBalance", [_sender.address, "latest"]), 16)
    gas_price = int(rpc_call("eth_gasPrice"), 16)
    if balance < AMOUNT_WEI + 21000 * gas_price:
        return {"ok": False, "error": "faucet_empty",
                "message": "Saldo faucet tidak cukup. Operator perlu mengisi ulang.",
                "faucet_balance_bkc": balance / 10**18}

    # Kirim — retry maks 3x bila nonce bertabrakan.
    last_err = None
    for _ in range(3):
        try:
            nonce = int(rpc_call("eth_getTransactionCount",
                                 [_sender.address, "pending"]), 16)
            tx = {"to": address, "value": AMOUNT_WEI, "gas": 21000,
                  "gasPrice": gas_price, "nonce": nonce, "chainId": CHAIN_ID}
            signed = _sender.sign_transaction(tx)
            tx_hash = rpc_call("eth_sendRawTransaction",
                               ["0x" + signed.raw_transaction.hex()])
            break
        except Exception as e:  # noqa: BLE001 — retry nonce race
            last_err = e
            time.sleep(1)
    else:
        return {"ok": False, "error": "send_failed",
                "message": f"Gagal mengirim transaksi: {last_err}"}

    receipt = None
    for _ in range(60):
        receipt = rpc_call("eth_getTransactionReceipt", [tx_hash])
        if receipt:
            break
        time.sleep(1)
    if not receipt or receipt.get("status") != "0x1":
        return {"ok": False, "error": "no_receipt",
                "message": "Transaksi terkirim tapi receipt tidak terkonfirmasi.",
                "tx_hash": tx_hash}

    _claims[addr] = {"last_claim": now, "tx_hash": tx_hash,
                     "count": prev["count"] + 1 if prev else 1}
    _ip_claims.setdefault(ip_hash, []).append(now)
    _ip_claims[ip_hash] = [t for t in _ip_claims[ip_hash]
                           if now - t < COOLDOWN_S]
    save_state()
    log_claim({"ts": now, "address": addr, "tx_hash": tx_hash,
               "amount_bkc": 100, "ip_hash": ip_hash,
               "block": int(receipt["blockNumber"], 16)})
    return {"ok": True, "tx_hash": tx_hash,
            "amount_bkc": 100,
            "block": int(receipt["blockNumber"], 16),
            "next_claim_at": now + COOLDOWN_S}


PAGE = """<!DOCTYPE html><html lang="id"><head><meta charset="utf-8">
<title>BLACKCHAIN Testnet Faucet</title>
<style>body{font-family:system-ui,sans-serif;max-width:560px;margin:40px auto;
padding:0 16px;background:#0b0f17;color:#e8eef7}
input,button{padding:10px;font-size:15px;width:100%;box-sizing:border-box;margin:6px 0}
button{background:#f5c518;border:0;font-weight:700;cursor:pointer}
a{color:#7cc7ff} pre{background:#131a26;padding:12px;overflow:auto}</style></head>
<body><h1>&#11042; BLACKCHAIN Testnet Faucet</h1>
<p>100 tBKC per alamat per 24 jam. Chain ID 20261120. Token testnet — tanpa nilai.</p>
<p>Anti-Sybil: proof-of-work ringan di browser (bukan hCaptcha) + cooldown + batas IP.</p>
<input id="addr" placeholder="0x... alamat EVM kamu">
<button onclick="claim()">Klaim 100 tBKC</button>
<pre id="out">Status faucet: <a href="/api/status">/api/status</a></pre>
<script>
async function claim(){
  const addr=document.getElementById('addr').value.trim();
  const out=document.getElementById('out');
  out.textContent='Meminta challenge...';
  let r=await fetch('/api/challenge?address='+encodeURIComponent(addr));
  let j=await r.json();
  if(!j.ok){out.textContent=JSON.stringify(j,null,2);return;}
  out.textContent='Mengerjakan proof-of-work...';
  let nonce=0, h='';
  const enc=new TextEncoder();
  while(true){
    h=await crypto.subtle.digest('SHA-256', enc.encode(addr.toLowerCase()+':'+j.challenge+':'+nonce));
    const hex=[...new Uint8Array(h)].map(b=>b.toString(16).padStart(2,'0')).join('');
    if(hex.startsWith('0000')) break;
    nonce++;
  }
  out.textContent='Mengirim klaim (nonce '+nonce+')...';
  r=await fetch('/api/claim',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({address:addr,challenge:j.challenge,nonce:nonce})});
  j=await r.json();
  out.textContent=JSON.stringify(j,null,2);
}
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # log ringkas ke stdout saja
        sys.stderr.write(f"{self.address_string()} {a[0] % a[1:]}\n")

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        if self.path == "/":
            body = PAGE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/api/status":
            with _lock:
                balance = int(rpc_call(
                    "eth_getBalance", [_sender.address, "latest"]), 16)
                now = int(time.time())
                day_start = now - (now % 86400)
                spent = sum(AMOUNT_WEI for c in _claims.values()
                            if c["last_claim"] >= day_start)
                self._json({
                    "ok": True, "chain_id": CHAIN_ID,
                    "faucet_address": _sender.address,
                    "faucet_balance_bkc": balance / 10**18,
                    "amount_per_claim_bkc": 100, "cooldown_hours": 24,
                    "ip_daily_max": IP_DAILY_MAX,
                    "spent_today_bkc": spent / 10**18,
                    "global_daily_cap_bkc": GLOBAL_DAILY_CAP_WEI / 10**18,
                    "total_claims": len(_claims),
                    "pow_prefix": POW_PREFIX,
                    "captcha": "proof-of-work ringan (bukan hCaptcha)",
                })
        elif self.path.startswith("/api/challenge"):
            from urllib.parse import urlparse, parse_qs
            q = parse_qs(urlparse(self.path).query)
            addr = (q.get("address") or [""])[0]
            if not ADDR_RE.match(addr):
                return self._json({"ok": False, "error": "Alamat EVM tidak valid."}, 400)
            ch = secrets.token_hex(16)
            with _lock:
                _challenges[ch] = {"address": addr.lower(), "issued": time.time()}
            self._json({"ok": True, "challenge": ch, "pow_prefix": POW_PREFIX,
                        "hint": "sha256(f'{alamat}:{challenge}:{nonce}') harus diawali "
                                + POW_PREFIX})
        elif self.path.startswith("/api/claims/"):
            addr = self.path.rsplit("/", 1)[-1].lower()
            if not ADDR_RE.match(addr):
                return self._json({"ok": False, "error": "Alamat EVM tidak valid."}, 400)
            with _lock:
                c = _claims.get(addr)
            if not c:
                return self._json({"ok": True, "address": addr,
                                   "claimed_before": False})
            self._json({"ok": True, "address": addr, "claimed_before": True,
                        "last_claim": datetime.fromtimestamp(
                            c["last_claim"], tz=timezone.utc).isoformat(),
                        "tx_hash": c["tx_hash"], "count": c["count"],
                        "next_claim_at": datetime.fromtimestamp(
                            c["last_claim"] + COOLDOWN_S,
                            tz=timezone.utc).isoformat()})
        else:
            self._json({"ok": False, "error": "not found"}, 404)

    def do_POST(self):  # noqa: N802
        if self.path != "/api/claim":
            return self._json({"ok": False, "error": "not found"}, 404)
        try:
            n = int(self.headers.get("Content-Length") or 0)
            data = json.loads(self.rfile.read(n) or b"{}")
        except Exception:  # noqa: BLE001
            return self._json({"ok": False, "error": "JSON tidak valid."}, 400)
        addr = str(data.get("address") or "")
        if not ADDR_RE.match(addr):
            return self._json({"ok": False, "error": "Alamat EVM tidak valid."}, 400)
        with _lock:
            ok, msg = verify_pow(addr, str(data.get("challenge") or ""),
                                 str(data.get("nonce") or ""))
            if not ok:
                return self._json({"ok": False, "error": "pow_failed",
                                   "message": msg}, 400)
            res = do_claim(addr, self.address_string())
        self._json(res, 200 if res["ok"] else 400)


if __name__ == "__main__":
    import sys
    load_state()
    sender = load_sender()
    print(f"faucet sender: {sender.address} (kunci hanya di memori)")
    print(f"faucet RPC: {RPC_URL} chain {CHAIN_ID} port {PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
