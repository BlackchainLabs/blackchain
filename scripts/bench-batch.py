#!/usr/bin/env python3
"""BLACKCHAIN Fase 1 — E2 batch benchmark (Sesi 9, 2026-11-20).

Measures the eth_sendRawTransactionBatch endpoint (fork) against the
single-tx endpoint baseline (E1, bench-evm.py):
  transfers-batch -- N accounts x M self-transfers, pre-signed UP FRONT
                    (signing excluded from the measured window), submitted
                    in batches of up to 100 txs.
  contract-batch  -- deploy SimpleCounter once (single endpoint), then N
                    increment() calls from one account, pre-signed,
                    submitted in batches of up to 100 txs.

Metrics: raw submit rate (tx/s, hashes returned), sustained TPS
(success / first-submit -> last-receipt window), latency p50/p95,
failed counts. Every number comes from a real measurement.

Security: test private keys live ONLY in --keys (mode 0600, under
~/workspace/.build-tmp/) and in process memory. Never printed, never
written under ~/workspace/blackchain/. Devnet-local only.

Usage:
  ~/workspace/.build-tmp/evmtest-venv/bin/python scripts/bench-batch.py \
      --mode transfers-batch --rpc http://127.0.0.1:8755 --chain-id 20261120 \
      --comet-rpc http://127.0.0.1:26877 --keys .../keys.json \
      --accounts 20 --txs-per-account 50 --batch-size 100 \
      --out .../e2-transfers-batch-run1.json
"""
import argparse
import json
import statistics
import sys
import time
import urllib.request

from eth_account import Account
from eth_utils import to_checksum_address

COUNTER_CREATION_BYTECODE = (
    "6080604052348015600e575f5ffd5b5061012f8061001c5f395ff3fe6080604052348015600e"
    "575f5ffd5b50600436106030575f3560e01c806361bc221a146034578063d09de08a14604e57"
    "5b5f5ffd5b603a6056565b604051604591906089565b60405180910390f35b6054605b565b00"
    "5b5f5481565b60015f5f828254606a919060cd565b92505081905550565b5f81905091905056"
    "5b6083816073565b82525050565b5f602082019050609a5f830184607c565b92915050565b7f"
    "4e487b71000000000000000000000000000000000000000000000000000000005f52601"
    "160045260245ffd5b5f60d5826073565b915060de836073565b92508282019050808211156"
    "0f35760f260a0565b5b9291505056fea2646970667358221220c81f22d8311ec135c0afe450"
    "b029cc468f45b86b6447809d2e06dee57cb40c7964736f6c634300081c0033"
)
INCREMENT_DATA = "0xd09de08a"
DEPLOY_GAS = 500_000
INCREMENT_GAS = 100_000


class Rpc:
    def __init__(self, url):
        self.url = url
        self._idx = 0

    def call(self, method, params=None):
        self._idx += 1
        body = json.dumps(
            {"jsonrpc": "2.0", "method": method, "params": params or [], "id": self._idx}
        ).encode()
        req = urllib.request.Request(
            self.url, data=body, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = json.load(r)
        if "error" in resp:
            raise RuntimeError(f"{method} error: {resp['error']}")
        return resp["result"]


def hexint(v):
    return int(v, 16) if isinstance(v, str) else int(v)


def wait_receipt(rpc, tx_hash, timeout=90):
    # Rpc.call returns the "result" field directly (not the envelope).
    t0 = time.time()
    while time.time() - t0 < timeout:
        rec = rpc.call("eth_getTransactionReceipt", [tx_hash])
        if rec:
            return rec
        time.sleep(0.5)
    return None


def comet_height(url):
    if not url:
        return None
    body = json.dumps({"jsonrpc": "2.0", "method": "status", "params": [], "id": 1}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return int(json.load(r)["result"]["sync_info"]["latest_block_height"])


def load_keys(path):
    # Same format as bench-evm.py generate: {"accounts": [{"address", "private_key"}]}
    with open(path) as f:
        data = json.load(f)
    accts = data["accounts"] if isinstance(data, dict) else data
    out = []
    for a in accts:
        acct = Account.from_key(a["private_key"])
        assert acct.address.lower() == a["address"].lower(), "keys file address mismatch"
        out.append(acct)
    return out


ZERO_HASH = "0x" + "00" * 32


def submit_batches(rpc, raw_txs, batch_size, batch_delay=0.0):
    """Submit pre-signed raw txs in batches. Returns (hashes, errors, submit_seconds).

    NOTE: a rejected tx comes back as {hash: 0x0000...0000, error: ...} —
    the zero hash is a NON-empty string, so it must be treated as a
    failure explicitly, never as a submitted hash (else the receipt phase
    polls the zero hash until timeout).
    """
    batches = [raw_txs[i:i + batch_size] for i in range(0, len(raw_txs), batch_size)]
    hashes, errors = [], []
    t0 = time.time()
    for bi, b in enumerate(batches):
        if bi > 0 and batch_delay > 0:
            time.sleep(batch_delay)
        results = rpc.call("eth_sendRawTransactionBatch", [b])
        for j, r in enumerate(results):
            if r.get("hash") and r["hash"] != ZERO_HASH:
                hashes.append(r["hash"])
            else:
                errors.append({"batch_index": j, "error": r.get("error", "unknown")})
    return hashes, errors, time.time() - t0


def run(args, rpc, raw_txs, label):
    n_total = len(raw_txs)
    block_before = hexint(rpc.call("eth_blockNumber", []))
    comet_before = comet_height(args.comet_rpc)
    t_start = time.time()
    hashes, errors, submit_seconds = submit_batches(rpc, raw_txs, args.batch_size, args.batch_delay)
    t_submit_done = time.time()
    submit_rate = len(hashes) / max(submit_seconds, 1e-9)
    print(f"[progress] submitted {len(hashes)}/{n_total} hashes, "
          f"{len(errors)} failed, in {submit_seconds:.2f}s "
          f"({submit_rate:.1f} tx/s)", file=sys.stderr, flush=True)

    latencies, failed = [], []
    # Poll receipts in parallel: a sequential 90s-timeout-per-tx loop turns
    # a handful of missing txs into an hour-long stall (observed in the
    # killed E2 runs). 20 workers, 45s per tx, results collected as they land.
    import concurrent.futures as _fut

    def _one(h):
        t_submit = t_submit_done
        rec = wait_receipt(rpc, h, 45)
        if rec is None:
            return (h, None, "receipt timeout")
        if rec.get("status") != "0x1":
            return (h, None, "receipt status != 0x1")
        return (h, time.time() - t_submit, None)

    with _fut.ThreadPoolExecutor(max_workers=20) as ex:
        # as_completed (NOT map): map yields in input order, so ONE slow
        # tx would stall all progress reporting and the whole phase.
        futs = {ex.submit(_one, h): h for h in hashes}
        for n, fut in enumerate(_fut.as_completed(futs)):
            h, lat, err = fut.result()
            if err:
                failed.append({"tx_hash": h, "error": err})
            else:
                latencies.append(lat)
            if n % 200 == 199:
                print(f"[progress] receipts resolved {n + 1}/{len(hashes)} "
                      f"({len(latencies)} ok, {len(failed)} failed) "
                      f"after {time.time() - t_submit_done:.1f}s",
                      file=sys.stderr, flush=True)
    t_end = time.time()
    window = max(t_end - t_start, 1e-9)
    lat_sorted = sorted(latencies)
    result = {
        "mode": label,
        "rpc": args.rpc,
        "chain_id": args.chain_id,
        "tx_planned": n_total,
        "tx_submitted_ok": len(hashes),
        "tx_failed_submit": len(errors),
        "tx_success": len(latencies),
        "tx_failed_receipt": len(failed),
        "submit_rate_tps": round(submit_rate, 2),
        "submit_seconds": round(submit_seconds, 3),
        "tps_sustained": round(len(latencies) / window, 2),
        "window_seconds": round(window, 3),
        "latency_p50_s": round(statistics.median(lat_sorted), 3) if lat_sorted else None,
        "latency_p95_s": round(lat_sorted[int(0.95 * len(lat_sorted))], 3) if lat_sorted else None,
        "block_before": block_before,
        "block_after": hexint(rpc.call("eth_blockNumber", [])),
        "comet_before": comet_before,
        "comet_after": comet_height(args.comet_rpc),
        "errors_sample": errors[:5],
        "failed_sample": failed[:5],
    }
    print(json.dumps(result, indent=2))
    if args.out:
        with open(args.out, "w") as f:
            json.dump(result, f, indent=2)
    return 0 if (len(latencies) == n_total and not errors) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=["transfers-batch", "contract-batch"])
    ap.add_argument("--rpc", required=True)
    ap.add_argument("--chain-id", type=int, required=True)
    ap.add_argument("--comet-rpc", default=None)
    ap.add_argument("--accounts", type=int, default=20)
    ap.add_argument("--txs-per-account", type=int, default=50)
    ap.add_argument("--calls", type=int, default=500)
    ap.add_argument("--batch-size", type=int, default=100)
    ap.add_argument("--batch-delay", type=float, default=0.2,
                    help="seconds between batch calls (keeps per-sender rate "
                         "under the 20 tx/s limiter when txs interleave)")
    ap.add_argument("--value", type=int, default=1)
    ap.add_argument("--gas", type=int, default=21_000)
    ap.add_argument("--keys", required=True)
    ap.add_argument("--receipt-timeout", type=int, default=90)
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    rpc = Rpc(args.rpc)
    chain = hexint(rpc.call("eth_chainId", []))
    if chain != args.chain_id:
        print(f"ERROR: chainId mismatch: {chain} != {args.chain_id}", file=sys.stderr)
        return 2
    gas_price = hexint(rpc.call("eth_gasPrice", []))
    print(f"chain {chain} ok | gasPrice={gas_price} wei", file=sys.stderr)

    if args.mode == "transfers-batch":
        accts = load_keys(args.keys)[: args.accounts]
        # Sign per account, then INTERLEAVE round-robin across senders so
        # each batch of 100 holds ~5 txs per sender (never a 50-tx burst
        # from one sender, which the 20 tx/s per-sender limiter would
        # reject). Nonce order per sender is preserved by the round-robin.
        per_acct_raw = []
        for a in accts:
            nonce = hexint(rpc.call("eth_getTransactionCount", [a.address, "pending"]))
            lst = []
            for i in range(args.txs_per_account):
                tx = {"chainId": args.chain_id, "nonce": nonce + i,
                      "to": to_checksum_address(a.address), "value": args.value,
                      "gas": args.gas, "gasPrice": gas_price}
                lst.append("0x" + a.sign_transaction(tx).raw_transaction.hex())
            per_acct_raw.append(lst)
        raw_txs = [tx for i in range(args.txs_per_account)
                   for tx in (per_acct_raw[a][i] for a in range(len(accts)))]
        print(f"pre-signed {len(raw_txs)} transfers ({len(accts)} accounts x "
              f"{args.txs_per_account}, interleaved); signing excluded from timing",
              file=sys.stderr)
        return run(args, rpc, raw_txs, "transfers-batch")

    # contract-batch: deploy from account 0, then increment() calls spread
    # over 20 accounts (5 per batch per sender at batch-size 100) so no
    # single sender bursts past the 20 tx/s per-sender limiter. (5 accounts
    # x 100 was tried first: each batch held 20 txs/sender and batches 2-5
    # were rate-limited, ~50% of calls never included — see docs/19 §5.2.)
    accts = load_keys(args.keys)[:20]
    a = accts[0]
    nonce = hexint(rpc.call("eth_getTransactionCount", [a.address, "pending"]))
    tx = {"chainId": args.chain_id, "nonce": nonce,
          "data": "0x" + COUNTER_CREATION_BYTECODE, "value": 0,
          "gas": DEPLOY_GAS, "gasPrice": gas_price}
    signed = a.sign_transaction(tx)
    deploy_hash = rpc.call("eth_sendRawTransaction", ["0x" + signed.raw_transaction.hex()])
    rec = wait_receipt(rpc, deploy_hash, args.receipt_timeout)
    assert rec and rec.get("status") == "0x1", f"deploy failed: {rec}"
    contract = rec["contractAddress"]
    print(f"deployed SimpleCounter at {contract}", file=sys.stderr)
    per_acct_calls = args.calls // len(accts)
    per_acct_raw = []
    for a in accts:
        nonce = hexint(rpc.call("eth_getTransactionCount", [a.address, "pending"]))
        lst = []
        for i in range(per_acct_calls):
            tx = {"chainId": args.chain_id, "nonce": nonce + i, "to": to_checksum_address(contract),
                  "data": INCREMENT_DATA, "value": 0,
                  "gas": INCREMENT_GAS, "gasPrice": gas_price}
            lst.append("0x" + a.sign_transaction(tx).raw_transaction.hex())
        per_acct_raw.append(lst)
    raw_txs = [tx for i in range(per_acct_calls)
               for tx in (per_acct_raw[a][i] for a in range(len(accts)))]
    print(f"pre-signed {len(raw_txs)} increment() calls (20 accounts x "
          f"{per_acct_calls}, interleaved); signing excluded from timing",
          file=sys.stderr)
    return run(args, rpc, raw_txs, "contract-batch")


if __name__ == "__main__":
    sys.exit(main())
