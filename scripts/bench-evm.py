#!/usr/bin/env python3
"""BLACKCHAIN EVM TPS benchmark harness (devnet-local only).

Modes:
  generate   -- create N fresh throwaway test accounts (keys in memory,
               addresses -> --addrs-out, private keys -> --keys-out).
  fund       -- fund the addresses in --addrs-out from the validator key
               in env PK_HEX (never printed). Amount is computed from the
               live gasPrice + planned load, or --fund-amount overrides it.
  transfers  -- N accounts x M self-transfers of --value wei, in parallel.
  contract   -- deploy one SimpleCounter, then N parallel increment() calls.

Security / honesty rules (see docs/08-benchmark-harness.md):
  * Devnet-local only. Never mainnet/Sepolia. Never request/store a seed
    phrase. The validator key is read ONLY from env PK_HEX in --fund mode
    and is NEVER printed, logged, or written to disk.
  * Test private keys live ONLY in the --keys-out JSON file (default under
    ~/workspace/.build-tmp/, mode 0600) and in process memory. They are
    NEVER written under ~/workspace/blackchain/ and NEVER printed.
  * --rpc, --chain-id and --comet-rpc are REQUIRED parameters (no
    hard-coded chain ID / ports): the same script must run unchanged
    against the current devnet and the future identity devnet.
  * Every number in the output comes from a real measurement. Failed or
    timed-out txs are counted as failed, never hidden or retried silently.

Dependencies: Python 3.10+ stdlib + eth_account (venv
~/workspace/.build-tmp/evmtest-venv). No web3 needed; JSON-RPC via urllib.

SimpleCounter (Solidity, compiled with solc 0.8.28 via solc-js):
    // SPDX-License-Identifier: MIT
    pragma solidity ^0.8.0;
    contract SimpleCounter {
        uint256 public counter;
        function increment() public { counter += 1; }
    }
  increment() selector 0xd09de08a, counter() selector 0x61bc221a.
  Creation bytecode below is the exact solc 0.8.28 output for that source
  (reproducible: /tmp/solcjs/SimpleCounter.sol + compile.js).
"""
import argparse
import json
import os
import statistics
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from eth_account import Account
from eth_utils import to_checksum_address

# --- SimpleCounter, solc 0.8.28 (see module docstring) -----------------------
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
INCREMENT_DATA = "0xd09de08a"   # increment()
COUNTER_DATA = "0x61bc221a"     # counter()
DEPLOY_GAS_FALLBACK = 500_000
INCREMENT_GAS_FALLBACK = 100_000


# --- JSON-RPC helpers --------------------------------------------------------
class Rpc:
    def __init__(self, url):
        self.url = url
        self._lock = threading.Lock()
        self._idx = 0

    def call(self, method, params=None):
        with self._lock:
            self._idx += 1
            idx = self._idx
        body = json.dumps(
            {"jsonrpc": "2.0", "method": method, "params": params or [], "id": idx}
        ).encode()
        req = urllib.request.Request(
            self.url, data=body, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            resp = json.load(r)
        if "error" in resp:
            raise RuntimeError(f"{method} error: {resp['error']}")
        if "result" not in resp:
            raise RuntimeError(f"{method} failed: {resp}")
        return resp["result"]


def hexint(v):
    return int(v, 16) if isinstance(v, str) else int(v)


def percentile(sorted_vals, p):
    if not sorted_vals:
        return None
    k = (len(sorted_vals) - 1) * p / 100.0
    f, c = int(k), min(int(k) + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


def wait_receipt(rpc, tx_hash, timeout):
    deadline = time.time() + timeout
    while time.time() < deadline:
        rec = rpc.call("eth_getTransactionReceipt", [tx_hash])
        if rec:
            return rec
        time.sleep(0.25)
    return None


def comet_height(comet_url):
    """Latest CometBFT height, or None if unreachable (reported honestly)."""
    if not comet_url:
        return None
    try:
        with urllib.request.urlopen(comet_url.rstrip("/") + "/status", timeout=5) as r:
            data = json.load(r)
        return int(data["result"]["sync_info"]["latest_block_height"])
    except Exception:
        return None


def block_stats(rpc, first, last):
    """Per-block tx counts + timestamps for [first, last] (cap 500 blocks)."""
    if last < first:
        return {"blocks_scanned": 0, "tx_per_block": [], "avg_block_time_s": None,
                "note": "empty block range"}
    if last - first + 1 > 500:
        first = last - 499  # cap; note it
        capped = True
    else:
        capped = False
    tx_counts, times = [], []
    for h in range(first, last + 1):
        blk = rpc.call("eth_getBlockByNumber", [hex(h), False])
        if blk is None:
            continue
        tx_counts.append(len(blk.get("transactions", [])))
        times.append(hexint(blk["timestamp"]))
    avg_bt = None
    if len(times) >= 2:
        diffs = [b - a for a, b in zip(times, times[1:]) if b > a]
        avg_bt = sum(diffs) / len(diffs) if diffs else 0.0
    return {"blocks_scanned": len(tx_counts), "tx_per_block": tx_counts,
            "avg_block_time_s": avg_bt,
            "total_txs_in_range": sum(tx_counts),
            "block_range": [first, last], "capped_to_500": capped}


def print_markdown_table(title, rows):
    print(f"\n## {title}\n")
    print("| metric | value |")
    print("|---|---|")
    for k, v in rows:
        print(f"| {k} | {v} |")


def save_json(path, obj):
    with open(path, "w") as f:
        json.dump(obj, f, indent=2)
    print(f"\nresults JSON: {path}")


# --- generate ----------------------------------------------------------------
def cmd_generate(args):
    accounts = []
    for _ in range(args.accounts):
        acct = Account.create()
        accounts.append({"address": acct.address, "private_key": acct.key.hex()})
    addrs = {"addresses": [a["address"] for a in accounts]}
    with open(args.addrs_out, "w") as f:
        json.dump(addrs, f, indent=2)
    with open(args.keys_out, "w") as f:
        json.dump({"accounts": accounts}, f, indent=2)
    os.chmod(args.keys_out, 0o600)
    print(f"generated {args.accounts} fresh test account(s)")
    print(f"addresses -> {args.addrs_out}")
    print(f"private keys -> {args.keys_out} (mode 0600, KEEP OUT of the repo)")
    print("addresses (fund these before running transfers/contract):")
    for a in addrs["addresses"]:
        print(f"  {a}")
    print("NOTE: private keys are NOT printed. They live only in the keys file.")


def load_keys(path):
    with open(path) as f:
        data = json.load(f)
    accts = data["accounts"] if isinstance(data, dict) else data
    out = []
    for a in accts:
        acct = Account.from_key(a["private_key"])
        assert acct.address.lower() == a["address"].lower(), "keys file address mismatch"
        out.append(acct)
    return out


def load_addrs(path):
    with open(path) as f:
        data = json.load(f)
    if isinstance(data, dict):
        return data.get("addresses") or [a["address"] for a in data["accounts"]]
    return list(data)


# --- fund --------------------------------------------------------------------
def cmd_fund(args):
    pk = os.environ.get("PK_HEX", "").strip()
    if not pk:
        print("ERROR: PK_HEX env var is not set (validator key required for --fund).",
              file=sys.stderr)
        sys.exit(2)
    rpc = Rpc(args.rpc)
    chain = hexint(rpc.call("eth_chainId", []))
    if chain != args.chain_id:
        print(f"ERROR: chainId mismatch: rpc reports {chain}, --chain-id is "
              f"{args.chain_id}. Refusing to fund on the wrong chain.",
              file=sys.stderr)
        sys.exit(2)
    funder = Account.from_key(pk)  # address printed; key never printed
    addrs = load_addrs(args.addrs)
    gas_price = hexint(rpc.call("eth_gasPrice", []))
    if args.fund_amount is not None:
        per_acct = args.fund_amount
        how = "explicit --fund-amount"
    elif args.fund_mode == "contract":
        per_acct = int((DEPLOY_GAS_FALLBACK
                        + args.txs_per_account * INCREMENT_GAS_FALLBACK)
                       * gas_price * 1.2) + 10_000
        how = "computed for contract mode"
    else:
        per_acct = int(args.txs_per_account * (args.value + 21_000 * gas_price)
                       * 1.2) + 10_000
        how = "computed for transfers mode"
    per_acct = max(per_acct, 1_000)
    bal = hexint(rpc.call("eth_getBalance", [funder.address, "latest"]))
    total_needed = per_acct * len(addrs)
    print(f"funder: {funder.address} balance={bal} wei")
    print(f"gasPrice={gas_price} wei | per-account funding={per_acct} wei ({how}) "
          f"x {len(addrs)} = {total_needed} wei")
    if bal < total_needed + 21_000 * gas_price * len(addrs):
        print(f"ERROR: funder balance {bal} wei is less than required "
              f"{total_needed} wei + gas. Aborting; nothing sent.", file=sys.stderr)
        sys.exit(1)
    nonce = hexint(rpc.call("eth_getTransactionCount", [funder.address, "pending"]))
    results = []
    for addr in addrs:
        tx = {"chainId": args.chain_id, "nonce": nonce,
              "to": to_checksum_address(addr),
              "value": per_acct, "gas": 21_000, "gasPrice": gas_price}
        signed = funder.sign_transaction(tx)
        tx_hash = rpc.call("eth_sendRawTransaction",
                           ["0x" + signed.raw_transaction.hex()])
        rec = wait_receipt(rpc, tx_hash, args.receipt_timeout)
        ok = bool(rec) and rec.get("status") == "0x1"
        print(f"fund {addr}: {per_acct} wei tx={tx_hash} "
              f"status={'OK' if ok else 'FAILED/NO-RECEIPT'}")
        results.append({"address": addr, "amount_wei": per_acct,
                        "tx_hash": tx_hash, "ok": ok})
        nonce += 1
    failed = [r for r in results if not r["ok"]]
    print(f"\nfunded {len(results) - len(failed)}/{len(results)} account(s)")
    if failed:
        print(f"WARNING: {len(failed)} funding tx(s) failed — see above.",
              file=sys.stderr)
        sys.exit(1)


# --- shared benchmark runner -------------------------------------------------
def run_benchmark(args, rpc, send_one, n_total, label):
    """send_one(acct_or_ctx, i) -> (tx_hash, submit_ts) or raises.
    Returns the results dict (latencies measured submit -> receipt)."""
    t_start_all = time.time()
    block_before = hexint(rpc.call("eth_blockNumber", []))
    comet_before = comet_height(args.comet_rpc)
    submitted, errors = [], []
    lock = threading.Lock()

    def worker(item):
        ctx, i = item
        try:
            tx_hash, t_submit = send_one(ctx, i)
            with lock:
                submitted.append((tx_hash, t_submit))
        except Exception as e:  # noqa: BLE001 - record honestly, keep going
            with lock:
                errors.append({"index": i, "error": str(e)})

    items = args.work_items  # list of (ctx, i)
    with ThreadPoolExecutor(max_workers=args.threads) as ex:
        list(ex.map(worker, items))
    t_submit_done = time.time()
    receipts, latencies, failed_receipts = [], [], []
    for tx_hash, t_submit in submitted:
        rec = wait_receipt(rpc, tx_hash, args.receipt_timeout)
        t_recv = time.time()
        if rec is None:
            failed_receipts.append({"tx_hash": tx_hash, "error": "receipt timeout"})
        elif rec.get("status") != "0x1":
            failed_receipts.append({"tx_hash": tx_hash, "error": "receipt status != 0x1"})
        else:
            receipts.append(rec)
            latencies.append(t_recv - t_submit)
    t_end_all = time.time()
    block_after = hexint(rpc.call("eth_blockNumber", []))
    comet_after = comet_height(args.comet_rpc)

    lat_sorted = sorted(latencies)
    window = max(t_end_all - t_start_all, 1e-9)
    n_ok = len(receipts)
    return {
        "label": label,
        "tx_planned": n_total,
        "tx_submitted": len(submitted),
        "tx_success": n_ok,
        "tx_failed_submit": len(errors),
        "tx_failed_receipt": len(failed_receipts),
        "submit_errors": errors[:20],
        "receipt_failures": failed_receipts[:20],
        "duration_submit_s": round(t_submit_done - t_start_all, 3),
        "duration_total_s": round(t_end_all - t_start_all, 3),
        "tps_success": round(n_ok / window, 3),
        "tps_submitted": round(len(submitted) / max(t_submit_done - t_start_all, 1e-9), 3),
        "latency_submit_to_receipt_s": {
            "p50": percentile(lat_sorted, 50),
            "p95": percentile(lat_sorted, 95),
            "max": max(lat_sorted) if lat_sorted else None,
            "mean": round(statistics.mean(lat_sorted), 3) if lat_sorted else None,
            "n": len(lat_sorted),
        },
        "block_before": block_before,
        "block_after": block_after,
        "block_stats": block_stats(rpc, block_before, block_after),
        "cometbft_height_before": comet_before,
        "cometbft_height_after": comet_after,
    }


def base_result(args, mode):
    params = {k: v for k, v in vars(args).items() if k != "work_items"}
    return {"mode": mode, "rpc": args.rpc, "chain_id": args.chain_id,
            "comet_rpc": args.comet_rpc,
            "generated_at_unix": time.time(), "params": params}


def print_results(result):
    r = result["result"]
    lat = r["latency_submit_to_receipt_s"]
    print_markdown_table("benchmark result", [
        ("mode", result["mode"]),
        ("rpc / chain_id", f"{result['rpc']} / {result['chain_id']}"),
        ("tx planned / submitted / success",
         f"{r['tx_planned']} / {r['tx_submitted']} / {r['tx_success']}"),
        ("tx failed (submit)", r["tx_failed_submit"]),
        ("tx failed (receipt/timeout)", r["tx_failed_receipt"]),
        ("duration total (s)", r["duration_total_s"]),
        ("TPS sustained (success / window)", r["tps_success"]),
        ("TPS submitted", r["tps_submitted"]),
        ("latency submit→receipt p50 (s)", lat["p50"]),
        ("latency submit→receipt p95 (s)", lat["p95"]),
        ("latency submit→receipt max (s)", lat["max"]),
        ("latency mean (s)", lat["mean"]),
        ("blocks", f"{r['block_before']} → {r['block_after']} "
         f"({r['block_stats']['blocks_scanned']} scanned, "
         f"{r['block_stats']['total_txs_in_range']} txs in range)"),
        ("avg block time (s)", r["block_stats"]["avg_block_time_s"]),
        ("tx per block", r["block_stats"]["tx_per_block"]),
        ("CometBFT height", f"{r['cometbft_height_before']} → "
         f"{r['cometbft_height_after']}"),
    ])
    if r["submit_errors"]:
        print("\nsubmit errors (first 20):")
        for e in r["submit_errors"]:
            print(f"  - {e}")
    if r["receipt_failures"]:
        print("\nreceipt failures (first 20):")
        for e in r["receipt_failures"]:
            print(f"  - {e}")


# --- transfers ---------------------------------------------------------------
def cmd_transfers(args):
    rpc = Rpc(args.rpc)
    chain = hexint(rpc.call("eth_chainId", []))
    if chain != args.chain_id:
        print(f"ERROR: chainId mismatch: rpc reports {chain}, --chain-id is "
              f"{args.chain_id}. Aborting.", file=sys.stderr)
        sys.exit(2)
    gas_price = hexint(rpc.call("eth_gasPrice", []))
    accts = load_keys(args.keys)[: args.accounts]
    if len(accts) < args.accounts:
        print(f"ERROR: keys file has {len(accts)} account(s), need {args.accounts}.",
              file=sys.stderr)
        sys.exit(2)
    per_acct_cost = args.txs_per_account * (args.value + args.gas * gas_price)
    for a in accts:
        bal = hexint(rpc.call("eth_getBalance", [a.address, "latest"]))
        if bal < per_acct_cost:
            print(f"ERROR: {a.address} balance {bal} wei < needed {per_acct_cost} "
                  f"wei for {args.txs_per_account} txs. Fund it first "
                  f"(bench-evm.py --mode fund). Aborting; nothing sent.",
                  file=sys.stderr)
            sys.exit(1)
    print(f"chain {chain} ok | gasPrice={gas_price} wei | {len(accts)} account(s) x "
          f"{args.txs_per_account} transfers of {args.value} wei (self-transfer)")
    nonces = {}
    for a in accts:
        nonces[a.address] = hexint(
            rpc.call("eth_getTransactionCount", [a.address, "pending"]))
    nonce_locks = {a.address: threading.Lock() for a in accts}

    def send_one(acct, i):
        with nonce_locks[acct.address]:
            nonce = nonces[acct.address]
            nonces[acct.address] += 1
        tx = {"chainId": args.chain_id, "nonce": nonce,
              "to": to_checksum_address(acct.address),
              "value": args.value, "gas": args.gas, "gasPrice": gas_price}
        signed = acct.sign_transaction(tx)
        t_submit = time.time()
        tx_hash = rpc.call("eth_sendRawTransaction",
                           ["0x" + signed.raw_transaction.hex()])
        return tx_hash, t_submit

    args.work_items = [(a, i) for a in accts for i in range(args.txs_per_account)]
    result = base_result(args, "transfers")
    result["result"] = run_benchmark(
        args, rpc, send_one, len(args.work_items), "transfers")
    result["result"]["gas_price_wei"] = gas_price
    result["result"]["accounts"] = [a.address for a in accts]
    print_results(result)
    if args.out:
        save_json(args.out, result)
    if result["result"]["tx_success"] < result["result"]["tx_planned"]:
        sys.exit(1)


# --- contract ----------------------------------------------------------------
def cmd_contract(args):
    rpc = Rpc(args.rpc)
    chain = hexint(rpc.call("eth_chainId", []))
    if chain != args.chain_id:
        print(f"ERROR: chainId mismatch: rpc reports {chain}, --chain-id is "
              f"{args.chain_id}. Aborting.", file=sys.stderr)
        sys.exit(2)
    gas_price = hexint(rpc.call("eth_gasPrice", []))
    accts = load_keys(args.keys)
    deployer = accts[0]
    nonce = hexint(rpc.call("eth_getTransactionCount", [deployer.address, "pending"]))
    try:
        deploy_gas = hexint(rpc.call("eth_estimateGas", [{
            "from": deployer.address, "data": "0x" + COUNTER_CREATION_BYTECODE}]))
    except Exception as e:  # noqa: BLE001
        print(f"eth_estimateGas for deploy failed ({e}); using fallback "
              f"{DEPLOY_GAS_FALLBACK}")
        deploy_gas = DEPLOY_GAS_FALLBACK
    deploy_gas = int(deploy_gas * 1.2) + 10_000
    bal = hexint(rpc.call("eth_getBalance", [deployer.address, "latest"]))
    need = deploy_gas * gas_price + args.calls * INCREMENT_GAS_FALLBACK * gas_price
    if bal < need:
        print(f"ERROR: deployer {deployer.address} balance {bal} wei < needed "
              f"~{need} wei (deploy + {args.calls} increments). Fund it first "
              f"(bench-evm.py --mode fund --fund-mode contract). Aborting; "
              f"nothing sent.", file=sys.stderr)
        sys.exit(1)
    print(f"deployer {deployer.address} balance={bal} wei | gasPrice={gas_price} | "
          f"deploy gas (est x1.2)={deploy_gas}")
    t_deploy0 = time.time()
    tx = {"chainId": args.chain_id, "nonce": nonce,
          "data": "0x" + COUNTER_CREATION_BYTECODE,
          "gas": deploy_gas, "gasPrice": gas_price}
    signed = deployer.sign_transaction(tx)
    tx_hash = rpc.call("eth_sendRawTransaction",
                       ["0x" + signed.raw_transaction.hex()])
    rec = wait_receipt(rpc, tx_hash, args.receipt_timeout)
    if not rec or rec.get("status") != "0x1":
        print(f"ERROR: contract deploy failed (tx {tx_hash}, receipt {rec}).",
              file=sys.stderr)
        sys.exit(1)
    # NOTE: Cosmos EVM receipts return contractAddress with non-EIP-55
    # casing; eth_account refuses to sign to a non-checksummed address,
    # so normalize it (same fix applies to every `to` in this script).
    contract = to_checksum_address(rec["contractAddress"])
    deploy_latency = round(time.time() - t_deploy0, 3)
    code = rpc.call("eth_getCode", [contract, "latest"])
    print(f"deployed SimpleCounter at {contract} in {deploy_latency}s "
          f"(deploy tx {tx_hash}, gasUsed {hexint(rec['gasUsed'])}, "
          f"code bytes {len(code) // 2 - 1})")
    try:
        inc_gas = hexint(rpc.call("eth_estimateGas", [
            {"from": deployer.address, "to": contract, "data": INCREMENT_DATA}]))
    except Exception as e:  # noqa: BLE001
        print(f"eth_estimateGas for increment failed ({e}); using fallback "
              f"{INCREMENT_GAS_FALLBACK}")
        inc_gas = INCREMENT_GAS_FALLBACK
    inc_gas = int(inc_gas * 1.2) + 10_000
    nonce = hexint(rpc.call("eth_getTransactionCount", [deployer.address, "pending"]))
    nonce_lock = threading.Lock()
    state = {"nonce": nonce}

    def send_one(_ctx, i):
        with nonce_lock:
            n = state["nonce"]
            state["nonce"] += 1
        tx = {"chainId": args.chain_id, "nonce": n, "to": contract,
              "value": 0, "gas": inc_gas, "gasPrice": gas_price,
              "data": INCREMENT_DATA}
        signed = deployer.sign_transaction(tx)
        t_submit = time.time()
        tx_hash = rpc.call("eth_sendRawTransaction",
                           ["0x" + signed.raw_transaction.hex()])
        return tx_hash, t_submit

    args.work_items = [(None, i) for i in range(args.calls)]
    result = base_result(args, "contract")
    result["result"] = run_benchmark(
        args, rpc, send_one, args.calls, "contract increment()")
    r = result["result"]
    r["deploy_tx_hash"] = tx_hash
    r["contract_address"] = contract
    r["deploy_latency_s"] = deploy_latency
    r["deploy_gas_used"] = hexint(rec["gasUsed"])
    r["increment_gas"] = inc_gas
    r["gas_price_wei"] = gas_price
    counter_hex = rpc.call("eth_call", [
        {"from": deployer.address, "to": contract, "data": COUNTER_DATA}, "latest"])
    r["counter_final"] = hexint(counter_hex)
    r["counter_matches_success"] = (r["counter_final"] == r["tx_success"])
    print_results(result)
    print(f"\nfinal counter() = {r['counter_final']} "
          f"(expected {r['tx_success']} successful increments; "
          f"match={r['counter_matches_success']})")
    if args.out:
        save_json(args.out, result)
    if r["tx_success"] < r["tx_planned"] or not r["counter_matches_success"]:
        sys.exit(1)


# --- CLI ---------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser(description="BLACKCHAIN EVM TPS benchmark harness")
    p.add_argument("--mode", required=True,
                   choices=["generate", "fund", "transfers", "contract"])
    p.add_argument("--rpc", help="EVM JSON-RPC URL (required except generate)")
    p.add_argument("--chain-id", type=int, help="EVM chain ID (required except generate)")
    p.add_argument("--comet-rpc", default=None,
                   help="CometBFT RPC URL for height cross-check (optional)")
    p.add_argument("--accounts", type=int, default=2)
    p.add_argument("--txs-per-account", type=int, default=10)
    p.add_argument("--calls", type=int, default=20)
    p.add_argument("--threads", type=int, default=0,
                   help="worker threads (0 = one per account / 4 for contract)")
    p.add_argument("--value", type=int, default=1, help="wei per transfer")
    p.add_argument("--gas", type=int, default=21_000, help="gas per transfer")
    p.add_argument("--addrs-out", default="",
                   help="generate: write addresses JSON here")
    p.add_argument("--keys-out", default="",
                   help="generate: write private keys JSON here (0600)")
    p.add_argument("--keys", default="", help="transfers/contract: keys JSON file")
    p.add_argument("--addrs", default="", help="fund: addresses JSON file")
    p.add_argument("--fund-amount", type=int, default=None,
                   help="fund: explicit wei per account (default: computed)")
    p.add_argument("--fund-mode", default="transfers",
                   choices=["transfers", "contract"],
                   help="fund: which planned load to size funding for")
    p.add_argument("--receipt-timeout", type=int, default=60)
    p.add_argument("--out", default="", help="write results JSON here")
    args = p.parse_args()

    if args.mode == "generate":
        if not args.addrs_out or not args.keys_out:
            p.error("--mode generate requires --addrs-out and --keys-out")
        cmd_generate(args)
        return
    if not args.rpc or args.chain_id is None:
        p.error(f"--mode {args.mode} requires --rpc and --chain-id")
    if args.mode == "fund":
        if not args.addrs:
            p.error("--mode fund requires --addrs")
        cmd_fund(args)
        return
    if not args.keys:
        p.error(f"--mode {args.mode} requires --keys")
    if args.threads <= 0:
        args.threads = args.accounts if args.mode == "transfers" else 4
    if args.mode == "transfers":
        cmd_transfers(args)
    else:
        cmd_contract(args)


if __name__ == "__main__":
    main()
