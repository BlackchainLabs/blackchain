#!/usr/bin/env python3
"""BlackScan Lite v0.1 (Sesi 12) — explorer minimal yang BENAR-BENAR JALAN.

BUKAN Blockscout. Blockscout penuh (Elixir + PostgreSQL 17 + archive node,
docs/11) terlalu berat untuk VM ini (1,5 CPU) dan untuk rantai ~800 blok.
Yang dibangun: indexer ringan Python stdlib + SQLite + halaman web sederhana.

Sumber data: EVM JSON-RPC val1 127.0.0.1:8655 (blok, tx, receipt) +
CometBFT RPC 127.0.0.1:26777 (proposer + app hash, diambil lazy di halaman
detail blok). Chain ID 20261120.

Fitur: daftar blok terbaru, detail blok, detail transaksi, saldo +
riwayat alamat, pencarian (hash tx / alamat / nomor blok), statistik,
API JSON minimal gaya Blockscout /api/v2.

Penggunaan:
  ./start.sh            # bind 127.0.0.1:8081
  curl localhost:8081/api/v2/stats
"""
import html
import json
import os
import sqlite3
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

EVM_RPC = os.environ.get("BLACKSCAN_EVM_RPC", "http://127.0.0.1:8655")
CMT_RPC = os.environ.get("BLACKSCAN_CMT_RPC", "http://127.0.0.1:26777")
PORT = int(os.environ.get("BLACKSCAN_PORT", "8081"))
POLL_S = 2
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DATA_DIR, "blackscan.db")

_db_lock = threading.RLock()  # RLock: _api memanggil indexed_height() saat lock dipegang
_indexed_height = -1
_indexer_error = ""


def rpc_call(method, params=None, url=EVM_RPC):
    body = json.dumps(
        {"jsonrpc": "2.0", "method": method, "params": params or [], "id": 1}
    ).encode()
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        out = json.load(r)
    if "error" in out:
        raise RuntimeError(f"{method} -> {out['error']}")
    return out["result"]


def cmt_get(path):
    with urllib.request.urlopen(CMT_RPC + path, timeout=10) as r:
        return json.load(r)["result"]


def db():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""CREATE TABLE IF NOT EXISTS blocks(
        number INTEGER PRIMARY KEY, hash TEXT UNIQUE, parent_hash TEXT,
        timestamp INTEGER, gas_used INTEGER, gas_limit INTEGER,
        tx_count INTEGER, miner TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS txs(
        hash TEXT PRIMARY KEY, block_number INTEGER, tx_index INTEGER,
        from_addr TEXT, to_addr TEXT, value_wei TEXT, gas INTEGER,
        gas_price TEXT, nonce INTEGER, input TEXT, status TEXT,
        gas_used INTEGER, FOREIGN KEY(block_number) REFERENCES blocks(number))""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_txs_from ON txs(from_addr)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_txs_to ON txs(to_addr)")
    conn.execute("""CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT)""")
    conn.commit()
    return conn


CONN = db()


def indexed_height():
    with _db_lock:
        row = CONN.execute(
            "SELECT value FROM meta WHERE key='height'").fetchone()
    return int(row[0]) if row else -1


def index_block(n):
    """Index satu blok EVM + receipt-nya. Kembalikan True bila ada blok."""
    block = rpc_call("eth_getBlockByNumber", [hex(n), True])
    if not block:
        return False
    receipts = rpc_call("eth_getBlockReceipts", [hex(n)]) or []
    rmap = {r["transactionHash"].lower(): r for r in receipts}
    with _db_lock:
        CONN.execute(
            "INSERT OR REPLACE INTO blocks VALUES (?,?,?,?,?,?,?,?)",
            (n, block["hash"], block["parentHash"],
             int(block["timestamp"], 16), int(block["gasUsed"], 16),
             int(block["gasLimit"], 16), len(block["transactions"]),
             block.get("miner")))
        for tx in block["transactions"]:
            r = rmap.get(tx["hash"].lower(), {})
            CONN.execute(
                """INSERT OR REPLACE INTO txs VALUES
                   (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (tx["hash"], n, int(tx["transactionIndex"], 16),
                 tx["from"].lower(), (tx.get("to") or "").lower(),
                 str(int(tx["value"], 16)), int(tx["gas"], 16),
                 tx.get("gasPrice"), int(tx["nonce"], 16),
                 tx.get("input") or "0x",
                 r.get("status"),
                 int(r["gasUsed"], 16) if r.get("gasUsed") else None))
        CONN.execute("INSERT OR REPLACE INTO meta VALUES ('height', ?)",
                     (str(n),))
        CONN.commit()
    return True


def indexer_loop():
    global _indexed_height, _indexer_error
    while True:
        try:
            head = int(rpc_call("eth_blockNumber"), 16)
            cur = indexed_height()
            # Blok EVM 0 adalah alias blok CometBFT 1 — mulai backfill dari 1.
            start = max(cur + 1, 1)
            # Backfill / kejar head, maks 50 blok per putaran agar UI tetap responsif.
            for n in range(start, min(head, start + 49) + 1):
                if not index_block(n):
                    break
            new_h = indexed_height()
            if new_h != _indexed_height:
                _indexed_height = new_h
                if new_h % 100 == 0 or new_h == head:
                    print(f"indexer: height {new_h}/{head}", flush=True)
            _indexer_error = ""
        except Exception as e:  # noqa: BLE001 — indexer tidak boleh mati
            _indexer_error = str(e)[:200]
        time.sleep(POLL_S)


# ---------- helpers tampilan ----------
def h(x):
    return html.escape(str(x))


def fmt_bkc(wei_str):
    try:
        return f"{int(wei_str) / 10**18:.6f}".rstrip("0").rstrip(".") or "0"
    except (TypeError, ValueError):
        return "0"


def page(title, body):
    return f"""<!DOCTYPE html><html lang="id"><head><meta charset="utf-8">
<title>{h(title)} — BlackScan Lite</title>
<style>body{{font-family:system-ui,sans-serif;max-width:900px;margin:24px auto;
padding:0 16px;background:#0b0f17;color:#e8eef7}}
a{{color:#7cc7ff}} table{{border-collapse:collapse;width:100%}}
td,th{{border:1px solid #263248;padding:6px 8px;text-align:left;font-size:14px}}
th{{background:#131a26}} .mono{{font-family:monospace;word-break:break-all}}
input{{padding:8px;width:70%}} button{{padding:8px 14px;background:#f5c518;border:0;font-weight:700}}
small{{color:#9fb0c3}}</style></head><body>
<h1><a href="/" style="color:#f5c518;text-decoration:none">&#11042; BlackScan Lite</a>
<small>BLACKCHAIN testnet &middot; chain ID 20261120 &middot; BUKAN Blockscout</small></h1>
<form action="/search" method="get"><input name="q" placeholder="Cari: hash tx / alamat 0x... / nomor blok">
<button>Cari</button></form><hr>{body}</body></html>""".encode()


def row_block(b):
    return (f"<tr><td><a href=\"/block/{b[0]}\">{b[0]}</a></td>"
            f"<td class=\"mono\"><a href=\"/block/{b[0]}\">{h(b[1][:18])}…</a></td>"
            f"<td>{time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(b[3]))} UTC</td>"
            f"<td>{b[5]}</td><td>{b[4]:,}</td></tr>")


def row_tx(t):
    to = f"<a href=\"/address/{t[4]}\">{h(t[4][:12])}…</a>" if t[4] else "(pembuatan kontrak)"
    status = t[10] if t[10] else "?"
    ok = "&#10003;" if status == "0x1" else ("&#10007;" if status == "0x0" else "?")
    return (f"<tr><td class=\"mono\"><a href=\"/tx/{t[0]}\">{h(t[0][:18])}…</a></td>"
            f"<td><a href=\"/block/{t[1]}\">{t[1]}</a></td>"
            f"<td class=\"mono\"><a href=\"/address/{t[3]}\">{h(t[3][:12])}…</a></td>"
            f"<td>{to}</td><td>{fmt_bkc(t[5])} BKC</td><td>{ok}</td></tr>")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, body, ctype="text/html; charset=utf-8", code=200):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(json.dumps(obj).encode(), "application/json", code)

    def do_GET(self):  # noqa: N802
        from urllib.parse import urlparse, parse_qs
        u = urlparse(self.path)
        path, q = u.path, parse_qs(u.query)
        try:
            if path == "/":
                self._home()
            elif path.startswith("/api/"):
                self._api(path, q)
            elif path.startswith("/block/"):
                self._block(path.rsplit("/", 1)[-1])
            elif path.startswith("/tx/"):
                self._tx(path.rsplit("/", 1)[-1])
            elif path.startswith("/address/"):
                self._address(path.rsplit("/", 1)[-1])
            elif path == "/search":
                self._search((q.get("q") or [""])[0].strip())
            else:
                self._send(page("Tidak ditemukan", "<p>Halaman tidak ada.</p>"), code=404)
        except Exception as e:  # noqa: BLE001
            self._send(page("Error", f"<p>Error: {h(e)}</p>"), code=500)

    # ----- halaman -----
    def _home(self):
        with _db_lock:
            blocks = CONN.execute(
                "SELECT * FROM blocks ORDER BY number DESC LIMIT 15").fetchall()
            txs = CONN.execute(
                "SELECT * FROM txs ORDER BY block_number DESC, tx_index DESC LIMIT 15").fetchall()
            nb = CONN.execute("SELECT COUNT(*) FROM blocks").fetchone()[0]
            nt = CONN.execute("SELECT COUNT(*) FROM txs").fetchone()[0]
        lag = ""
        try:
            head = int(rpc_call("eth_blockNumber"), 16)
            lag = f" &middot; head chain {head} &middot; ter-index {_indexed_height} (lag {head - _indexed_height})"
        except Exception:  # noqa: BLE001
            lag = " &middot; head chain tidak terbaca"
        body = (f"<p>{nb} blok &middot; {nt} transaksi ter-index{lag}"
                + (f" &middot; <b>indexer error:</b> {h(_indexer_error)}" if _indexer_error else "")
                + "</p><h2>Blok terbaru</h2><table><tr><th>Blok</th><th>Hash</th>"
                "<th>Waktu (UTC)</th><th>Tx</th><th>Gas used</th></tr>"
                + "".join(row_block(b) for b in blocks) + "</table>"
                "<h2>Transaksi terbaru</h2><table><tr><th>Hash</th><th>Blok</th>"
                "<th>Dari</th><th>Ke</th><th>Nilai</th><th>Status</th></tr>"
                + "".join(row_tx(t) for t in txs) + "</table>")
        self._send(page("Beranda", body))

    def _block(self, key):
        with _db_lock:
            if key.startswith("0x"):
                b = CONN.execute("SELECT * FROM blocks WHERE hash=?",
                                 (key.lower(),)).fetchone()
            else:
                b = CONN.execute("SELECT * FROM blocks WHERE number=?",
                                 (int(key),)).fetchone()
            txs = CONN.execute(
                "SELECT * FROM txs WHERE block_number=? ORDER BY tx_index",
                (b[0],)).fetchall() if b else []
        if not b:
            return self._send(page("Blok tidak ditemukan",
                                   "<p>Blok belum ter-index / tidak ada.</p>"), code=404)
        proposer, app_hash = "?", "?"
        try:
            hdr = cmt_get(f"/block?height={b[0]}")["block"]["header"]
            proposer = hdr["proposer_address"]
            app_hash = hdr["app_hash"]
        except Exception:  # noqa: BLE001 — data CometBFT opsional
            pass
        body = (f"<h2>Blok {b[0]}</h2><table>"
                f"<tr><th>Hash</th><td class=\"mono\">{h(b[1])}</td></tr>"
                f"<tr><th>Parent</th><td class=\"mono\">{h(b[2])}</td></tr>"
                f"<tr><th>Waktu</th><td>{time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(b[3]))} UTC</td></tr>"
                f"<tr><th>Proposer (CometBFT)</th><td class=\"mono\">{h(proposer)}</td></tr>"
                f"<tr><th>App hash</th><td class=\"mono\">{h(app_hash)}</td></tr>"
                f"<tr><th>Gas used / limit</th><td>{b[4]:,} / {b[5]:,}</td></tr>"
                f"<tr><th>Tx</th><td>{b[6]}</td></tr></table>"
                "<h3>Transaksi</h3><table><tr><th>Hash</th><th>Blok</th><th>Dari</th>"
                "<th>Ke</th><th>Nilai</th><th>Status</th></tr>"
                + "".join(row_tx(t) for t in txs) + "</table>")
        self._send(page(f"Blok {b[0]}", body))

    def _tx(self, txhash):
        with _db_lock:
            t = CONN.execute("SELECT * FROM txs WHERE hash=?",
                             (txhash.lower(),)).fetchone()
        if not t:
            return self._send(page("Transaksi tidak ditemukan",
                                   "<p>Tx belum ter-index / tidak ada.</p>"), code=404)
        to = f"<a href=\"/address/{t[4]}\">{h(t[4])}</a>" if t[4] else "(pembuatan kontrak)"
        status = "Sukses" if t[10] == "0x1" else ("Gagal" if t[10] == "0x0" else "?")
        body = (f"<h2>Transaksi</h2><table>"
                f"<tr><th>Hash</th><td class=\"mono\">{h(t[0])}</td></tr>"
                f"<tr><th>Blok</th><td><a href=\"/block/{t[1]}\">{t[1]}</a> (index {t[2]})</td></tr>"
                f"<tr><th>Status</th><td>{status}</td></tr>"
                f"<tr><th>Dari</th><td class=\"mono\"><a href=\"/address/{t[3]}\">{h(t[3])}</a></td></tr>"
                f"<tr><th>Ke</th><td class=\"mono\">{to}</td></tr>"
                f"<tr><th>Nilai</th><td>{fmt_bkc(t[5])} BKC ({t[5]} wei)</td></tr>"
                f"<tr><th>Gas / gas used</th><td>{t[6]:,} / {t[11] if t[11] is not None else '?'}</td></tr>"
                f"<tr><th>Gas price</th><td>{t[7]}</td></tr>"
                f"<tr><th>Nonce</th><td>{t[8]}</td></tr>"
                f"<tr><th>Input</th><td class=\"mono\">{h(t[9][:200])}</td></tr></table>")
        self._send(page("Transaksi", body))

    def _address(self, addr):
        addr = addr.lower()
        try:
            bal = int(rpc_call("eth_getBalance", [addr, "latest"]), 16)
            nonce = int(rpc_call("eth_getTransactionCount", [addr, "latest"]), 16)
        except Exception:  # noqa: BLE001
            bal, nonce = 0, 0
        with _db_lock:
            txs = CONN.execute(
                """SELECT * FROM txs WHERE from_addr=? OR to_addr=?
                   ORDER BY block_number DESC, tx_index DESC LIMIT 50""",
                (addr, addr)).fetchall()
        body = (f"<h2>Alamat</h2><table>"
                f"<tr><th>Alamat</th><td class=\"mono\">{h(addr)}</td></tr>"
                f"<tr><th>Saldo</th><td>{bal / 10**18} BKC ({bal} wei)</td></tr>"
                f"<tr><th>Nonce</th><td>{nonce}</td></tr>"
                f"<tr><th>Transaksi tercatat</th><td>{len(txs)} (maks 50 terbaru)</td></tr></table>"
                "<h3>Riwayat transaksi</h3><table><tr><th>Hash</th><th>Blok</th><th>Dari</th>"
                "<th>Ke</th><th>Nilai</th><th>Status</th></tr>"
                + "".join(row_tx(t) for t in txs) + "</table>")
        self._send(page("Alamat", body))

    def _search(self, query):
        import re
        if re.fullmatch(r"0x[0-9a-fA-F]{64}", query):
            with _db_lock:
                t = CONN.execute("SELECT 1 FROM txs WHERE hash=?",
                                 (query.lower(),)).fetchone()
                b = CONN.execute("SELECT 1 FROM blocks WHERE hash=?",
                                 (query.lower(),)).fetchone()
            if t:
                return self._tx(query)
            if b:
                return self._block(query)
            return self._send(page("Tidak ditemukan",
                                   f"<p>Hash {h(query)} belum ter-index.</p>"), code=404)
        if re.fullmatch(r"0x[0-9a-fA-F]{40}", query):
            return self._address(query)
        if query.isdigit():
            return self._block(query)
        self._send(page("Tidak ditemukan",
                        f"<p>Pencarian '{h(query)}' tidak cocok: pakai hash tx (66 karakter), "
                        "alamat 0x (42 karakter), atau nomor blok.</p>"), code=404)

    # ----- API -----
    def _api(self, path, q):
        parts = [p for p in path.split("/") if p]
        with _db_lock:
            if parts == ["api", "v2", "blocks"]:
                rows = CONN.execute(
                    "SELECT * FROM blocks ORDER BY number DESC LIMIT 20").fetchall()
                return self._json({"blocks": [
                    {"number": r[0], "hash": r[1], "timestamp": r[3],
                     "gas_used": r[4], "tx_count": r[5]} for r in rows]})
            if len(parts) == 4 and parts[:3] == ["api", "v2", "blocks"]:
                key = parts[3]
                b = (CONN.execute("SELECT * FROM blocks WHERE hash=?", (key.lower(),)).fetchone()
                     if key.startswith("0x") else
                     CONN.execute("SELECT * FROM blocks WHERE number=?", (int(key),)).fetchone())
                if not b:
                    return self._json({"error": "block not found"}, 404)
                txs = CONN.execute(
                    "SELECT hash FROM txs WHERE block_number=? ORDER BY tx_index",
                    (b[0],)).fetchall()
                return self._json({"number": b[0], "hash": b[1], "parent_hash": b[2],
                                   "timestamp": b[3], "gas_used": b[4],
                                   "gas_limit": b[5], "tx_count": b[6],
                                   "miner": b[7], "transactions": [t[0] for t in txs]})
            if parts == ["api", "v2", "transactions"]:
                rows = CONN.execute(
                    "SELECT * FROM txs ORDER BY block_number DESC, tx_index DESC LIMIT 20").fetchall()
                return self._json({"transactions": [self._tx_json(r) for r in rows]})
            if len(parts) == 4 and parts[:3] == ["api", "v2", "transactions"]:
                t = CONN.execute("SELECT * FROM txs WHERE hash=?",
                                 (parts[3].lower(),)).fetchone()
                if not t:
                    return self._json({"error": "transaction not found"}, 404)
                return self._json(self._tx_json(t))
            if len(parts) == 4 and parts[:3] == ["api", "v2", "addresses"]:
                addr = parts[3].lower()
                bal = int(rpc_call("eth_getBalance", [addr, "latest"]), 16)
                return self._json({"address": addr, "balance_wei": str(bal),
                                   "balance_bkc": bal / 10**18})
            if (len(parts) == 5 and parts[:3] == ["api", "v2", "addresses"]
                    and parts[4] == "transactions"):
                addr = parts[3].lower()
                rows = CONN.execute(
                    """SELECT * FROM txs WHERE from_addr=? OR to_addr=?
                       ORDER BY block_number DESC, tx_index DESC LIMIT 20""",
                    (addr, addr)).fetchall()
                return self._json({"transactions": [self._tx_json(r) for r in rows]})
            if parts == ["api", "v2", "stats"]:
                nb = CONN.execute("SELECT COUNT(*) FROM blocks").fetchone()[0]
                nt = CONN.execute("SELECT COUNT(*) FROM txs").fetchone()[0]
                first = CONN.execute("SELECT MIN(timestamp) FROM blocks").fetchone()[0]
                last = CONN.execute("SELECT MAX(timestamp) FROM blocks").fetchone()[0]
                avg = (last - first) / max(nb - 1, 1) if nb > 1 else 0
                return self._json({"chain_id": 20261120, "blocks_indexed": nb,
                                   "transactions_indexed": nt,
                                   "indexed_height": indexed_height(),
                                   "avg_block_time_s": round(avg, 2),
                                   "indexer_error": _indexer_error})
            if parts == ["api", "v2", "search"]:
                query = (q.get("q") or [""])[0].strip()
                return self._json({"q": query,
                                   "hint": "Gunakan halaman /search untuk hasil lengkap."})
        if parts == ["api", "health"]:
            return self._json({"ok": not _indexer_error,
                               "indexed_height": indexed_height(),
                               "error": _indexer_error})
        return self._json({"error": "not found"}, 404)

    @staticmethod
    def _tx_json(r):
        return {"hash": r[0], "block_number": r[1], "tx_index": r[2],
                "from": r[3], "to": r[4], "value_wei": r[5],
                "value_bkc": int(r[5]) / 10**18, "gas": r[6],
                "gas_price": r[7], "nonce": r[8], "status": r[10],
                "gas_used": r[11]}


if __name__ == "__main__":
    threading.Thread(target=indexer_loop, daemon=True).start()
    print(f"blackscan lite: EVM {EVM_RPC} CometBFT {CMT_RPC} port {PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
