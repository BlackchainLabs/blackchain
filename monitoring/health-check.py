#!/usr/bin/env python3
"""BLACKCHAIN health-check (Sesi 12, P6) — cek sekali jalan, tulis status JSON + log.

Yang dicek (semua lokal, 127.0.0.1):
- Devnet BKC CometBFT 26677 + EVM 8555
- Validator testnet val1..val4 CometBFT 26777/26787/26797/26807 + EVM 8655 (val1)
- Faucet 8080 /api/status, BlackScan 8081 /api/health

Deteksi:
- DOWN: RPC/HTTP tidak menjawab dalam timeout.
- HALT: height tidak berubah dibanding run sebelumnya (state di data/prev.json).
- FORK: validator yang hidup tidak sepakat hash pada height yang sama.
- LAGGING: catching_up == true, atau BlackScan lag > 10 blok dari head.

Penggunaan:
  ./health-check.py            # exit 0 OK, 1 WARNING, 2 CRITICAL
  python3 health-check.py --once
Dijadwalkan tiap menit (cron, oleh Muse utama — lihat docs/24):
  * * * * * /usr/bin/python3 /home/hatch/workspace/blackchain/repo/monitoring/health-check.py >> /home/hatch/workspace/blackchain/repo/monitoring/data/health.log 2>&1

Stdlib saja. Tidak mengubah node apa pun (hanya baca RPC/HTTP).
"""
import json
import os
import sys
import time
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")
PREV_FILE = os.path.join(DATA_DIR, "prev.json")
STATUS_FILE = os.path.join(DATA_DIR, "status.json")
TIMEOUT = 5

NODES = [
    {"name": "devnet", "cmt": 26677, "evm": 8555},
    {"name": "val1", "cmt": 26777, "evm": 8655},
    {"name": "val2", "cmt": 26787, "evm": 8665},
    {"name": "val3", "cmt": 26797, "evm": 8675},
    {"name": "val4", "cmt": 26807, "evm": 8685},
]


def http_json(url, data=None, timeout=TIMEOUT):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json"} if body else {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def check_cmt(port):
    st = http_json(f"http://127.0.0.1:{port}/status")
    si = st["result"]["sync_info"]
    peers = http_json(f"http://127.0.0.1:{port}/net_info")["result"]["n_peers"]
    return {"height": int(si["latest_block_height"]),
            "hash": si["latest_block_hash"],
            "catching_up": si["catching_up"], "peers": int(peers)}


def check_evm(port):
    out = http_json(f"http://127.0.0.1:{port}",
                    {"jsonrpc": "2.0", "method": "eth_blockNumber",
                     "params": [], "id": 1})
    chain = http_json(f"http://127.0.0.1:{port}",
                      {"jsonrpc": "2.0", "method": "eth_chainId",
                       "params": [], "id": 1})
    return {"block": int(out["result"], 16), "chain_id": chain["result"]}


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    now = int(time.time())
    prev = {}
    if os.path.exists(PREV_FILE):
        try:
            prev = json.load(open(PREV_FILE))
        except Exception:  # noqa: BLE001
            prev = {}
    status = {"ts": now, "ts_iso": time.strftime(
        "%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)), "nodes": {},
              "services": {}, "problems": []}
    worst = 0  # 0 ok, 1 warning, 2 critical

    for n in NODES:
        entry = {"name": n["name"]}
        try:
            c = check_cmt(n["cmt"])
            entry.update(c)
            entry["cmt"] = "up"
            p = prev.get(n["name"], {})
            if p.get("height") == c["height"] and p.get("height") is not None:
                entry["halted"] = True
                status["problems"].append(
                    f"HALT? {n['name']} height diam di {c['height']} (2 cek berturut-turut)")
                worst = max(worst, 2)
            else:
                entry["halted"] = False
            if c["catching_up"]:
                entry["lagging"] = True
                status["problems"].append(f"LAGGING {n['name']} catching_up=true")
                worst = max(worst, 1)
        except Exception as e:  # noqa: BLE001
            entry["cmt"] = "down"
            entry["error"] = str(e)[:120]
            status["problems"].append(f"DOWN {n['name']} CometBFT :{n['cmt']} ({e})")
            worst = max(worst, 2)
        try:
            e = check_evm(n["evm"])
            entry["evm"] = "up"
            entry["evm_block"] = e["block"]
            if e["chain_id"] != "0x1352900":
                entry["evm_chain_ok"] = False
                status["problems"].append(
                    f"CHAIN ID SALAH {n['name']} EVM :{n['evm']} = {e['chain_id']}")
                worst = max(worst, 2)
            else:
                entry["evm_chain_ok"] = True
        except Exception as e:  # noqa: BLE001
            entry["evm"] = "down"
            entry["evm_error"] = str(e)[:120]
            status["problems"].append(f"DOWN {n['name']} EVM :{n['evm']} ({e})")
            worst = max(worst, 2)
        status["nodes"][n["name"]] = entry

    # Fork antar validator: hash harus sama pada height yang sama.
    alive = [v for k, v in status["nodes"].items()
             if k.startswith("val") and v.get("cmt") == "up"]
    by_height = {}
    for v in alive:
        by_height.setdefault(v["height"], set()).add(v["hash"])
    for hgt, hashes in by_height.items():
        if len(hashes) > 1:
            status["problems"].append(
                f"FORK? validator tidak sepakat hash pada height {hgt}: {sorted(hashes)}")
            worst = max(worst, 2)
    if len(alive) < 3 and len(alive) > 0:
        status["problems"].append(
            f"KUORUM RISIKO: hanya {len(alive)}/4 validator hidup (butuh >2/3)")
        worst = max(worst, 1)
    if len(alive) == 0:
        status["problems"].append("SEMUA validator testnet DOWN — chain halt")
        worst = max(worst, 2)

    # Layanan: faucet + blackscan.
    try:
        f = http_json("http://127.0.0.1:8080/api/status")
        status["services"]["faucet"] = {
            "up": True, "balance_bkc": f["faucet_balance_bkc"],
            "total_claims": f["total_claims"]}
        if f["faucet_balance_bkc"] < 100:
            status["problems"].append("FAUCET HAMPIR HABIS (<100 BKC)")
            worst = max(worst, 1)
    except Exception as e:  # noqa: BLE001
        status["services"]["faucet"] = {"up": False, "error": str(e)[:120]}
        status["problems"].append(f"DOWN faucet :8080 ({e})")
        worst = max(worst, 1)
    try:
        b = http_json("http://127.0.0.1:8081/api/health")
        s = http_json("http://127.0.0.1:8081/api/v2/stats")
        status["services"]["blackscan"] = {
            "up": True, "indexed_height": b["indexed_height"],
            "indexer_error": b.get("error", "")}
        head = status["nodes"].get("val1", {}).get("height")
        if head and b["indexed_height"] >= 0 and head - b["indexed_height"] > 10:
            status["problems"].append(
                f"BLACKSCAN LAG {head - b['indexed_height']} blok")
            worst = max(worst, 1)
        if b.get("error"):
            status["problems"].append(f"BLACKSCAN indexer error: {b['error']}")
            worst = max(worst, 1)
    except Exception as e:  # noqa: BLE001
        status["services"]["blackscan"] = {"up": False, "error": str(e)[:120]}
        status["problems"].append(f"DOWN blackscan :8081 ({e})")
        worst = max(worst, 1)

    status["level"] = ["OK", "WARNING", "CRITICAL"][worst]
    with open(STATUS_FILE, "w") as f:
        json.dump(status, f, indent=2)
    with open(PREV_FILE, "w") as f:
        json.dump({k: {"height": v.get("height")} for k, v in
                   status["nodes"].items() if v.get("height") is not None}, f)
    line = (f"{status['ts_iso']} {status['level']} "
            f"devnet={status['nodes'].get('devnet', {}).get('height')} "
            f"val={'/'.join(str(status['nodes'].get(f'val{i}', {}).get('height')) for i in (1, 2, 3, 4))} "
            f"problems={len(status['problems'])}")
    print(line)
    for p in status["problems"]:
        print("  ! " + p)
    return worst


if __name__ == "__main__":
    sys.exit(main())
