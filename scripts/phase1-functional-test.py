#!/usr/bin/env python3
"""BLACKCHAIN Fase 1 — functional test batch endpoint (Sesi 9, 2026-11-20).

Tests against the Phase 1 fork devnet (1 validator, local only):
  1. eth_chainId == 0x1352900 (20261120)
  2. single eth_sendRawTransaction transfer works
  3. eth_sendRawTransactionBatch of 10 transfers works (all hashes, no errors)
  4. error cases: batch of 101 txs rejected; one bad tx + one good tx in a
     batch (good succeeds, bad errors); duplicate tx in one batch rejected.

Security: the validator private key is exported IN-MEMORY ONLY via
`keys export` and is NEVER printed or written to disk. Test keys are
throwaway. Devnet-local only.

Usage:
  ~/workspace/.build-tmp/evmtest-venv/bin/python scripts/phase1-functional-test.py \
      --rpc http://127.0.0.1:8755 --chain-id 20261120
"""
import argparse
import json
import subprocess
import sys
import time
import urllib.request

from eth_account import Account

HOME = "/home/hatch/workspace/blackchain"
BIN = HOME + "/build/blackchaind-phase1"
NODE_HOME = HOME + "/phase1-data/cosmos"


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
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)


def hexint(v):
    return int(v, 16) if isinstance(v, str) else int(v)


def wait_receipt(rpc, tx_hash, timeout=60):
    t0 = time.time()
    while time.time() - t0 < timeout:
        resp = rpc.call("eth_getTransactionReceipt", [tx_hash])
        if resp.get("result"):
            return resp["result"]
        time.sleep(1)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rpc", required=True)
    ap.add_argument("--chain-id", type=int, required=True)
    args = ap.parse_args()
    rpc = Rpc(args.rpc)

    # 1. chainId
    resp = rpc.call("eth_chainId")
    chain_id = hexint(resp["result"])
    print(f"[1] eth_chainId = {hex(chain_id)} (expected 0x1352900)")
    assert chain_id == args.chain_id, "chainId mismatch"

    # Validator key, in-memory only.
    out = subprocess.check_output(
        [BIN, "keys", "export", "validator", "--keyring-backend", "test",
         "--home", NODE_HOME, "--unarmored-hex", "--unsafe", "-y"],
        text=True,
    )
    pk_hex = out.strip().splitlines()[-1].strip()
    acct = Account.from_key(pk_hex)
    sender = acct.address
    print(f"[k] validator ETH address: {sender}")

    nonce = hexint(rpc.call("eth_getTransactionCount", [sender, "pending"])["result"])
    gas_price = hexint(rpc.call("eth_gasPrice")["result"])
    print(f"[k] nonce={nonce} gasPrice={gas_price}")

    def sign_transfer(to, value, nonce_):
        tx = {
            "to": to,
            "value": value,
            "gas": 21000,
            "gasPrice": gas_price,
            "nonce": nonce_,
            "chainId": args.chain_id,
        }
        return acct.sign_transaction(tx).raw_transaction.hex()

    # 2. single transfer
    recv1 = Account.create().address
    raw1 = sign_transfer(recv1, 1_000_000, nonce)
    resp = rpc.call("eth_sendRawTransaction", ["0x" + raw1])
    assert "result" in resp, f"single send failed: {resp}"
    tx1 = resp["result"]
    print(f"[2] single tx hash: {tx1}")
    rcpt = wait_receipt(rpc, tx1)
    assert rcpt and rcpt["status"] == "0x1", f"single receipt bad: {rcpt}"
    bal = hexint(rpc.call("eth_getBalance", [recv1, "latest"])["result"])
    assert bal == 1_000_000, f"recipient balance {bal} != 1000000"
    print(f"[2] OK: receipt block {hexint(rcpt['blockNumber'])}, recipient +1,000,000 wei")

    # 3. batch of 10 transfers (same sender, sequential nonces)
    nonce = hexint(rpc.call("eth_getTransactionCount", [sender, "pending"])["result"])
    recvs = [Account.create().address for _ in range(10)]
    raws = ["0x" + sign_transfer(r, 1_000_000, nonce + i) for i, r in enumerate(recvs)]
    t0 = time.time()
    resp = rpc.call("eth_sendRawTransactionBatch", [raws])
    dt = time.time() - t0
    assert "result" in resp, f"batch call failed: {resp}"
    results = resp["result"]
    assert len(results) == 10, f"batch returned {len(results)} results"
    hashes = []
    for i, r in enumerate(results):
        assert r.get("hash") and not r.get("error"), f"batch item {i} bad: {r}"
        hashes.append(r["hash"])
    print(f"[3] batch OK: 10/10 hashes in {dt:.2f}s, first {hashes[0]}")
    for h in hashes:
        rcpt = wait_receipt(rpc, h)
        assert rcpt and rcpt["status"] == "0x1", f"batch receipt bad: {h} {rcpt}"
    for r in recvs:
        bal = hexint(rpc.call("eth_getBalance", [r, "latest"])["result"])
        assert bal == 1_000_000, f"batch recipient {r} balance {bal}"
    print("[3] OK: all 10 receipts status 0x1, all recipients +1,000,000 wei")

    # 4a. batch of 101 txs must be rejected
    nonce = hexint(rpc.call("eth_getTransactionCount", [sender, "pending"])["result"])
    raws101 = ["0x" + sign_transfer(Account.create().address, 1_000_000, nonce + i)
               for i in range(101)]
    resp = rpc.call("eth_sendRawTransactionBatch", [raws101])
    assert "error" in resp, f"101-tx batch should be rejected: {resp}"
    print(f"[4a] OK: 101-tx batch rejected: {resp['error']['message'][:80]}")

    # 4b. one bad tx + one good tx: good succeeds, bad errors, batch not failed
    nonce = hexint(rpc.call("eth_getTransactionCount", [sender, "pending"])["result"])
    good_recv = Account.create().address
    good_raw = "0x" + sign_transfer(good_recv, 1_000_000, nonce)
    bad_raw = "0xdeadbeef"  # invalid RLP
    resp = rpc.call("eth_sendRawTransactionBatch", [[bad_raw, good_raw]])
    assert "result" in resp, f"mixed batch failed: {resp}"
    res = resp["result"]
    assert res[0].get("error") and res[1].get("hash"), f"mixed batch wrong: {res}"
    rcpt = wait_receipt(rpc, res[1]["hash"])
    assert rcpt and rcpt["status"] == "0x1"
    print(f"[4b] OK: bad tx errored ({res[0]['error'][:60]}), good tx {res[1]['hash'][:18]}... succeeded")

    # 4c. duplicate tx twice in one batch: second rejected
    nonce = hexint(rpc.call("eth_getTransactionCount", [sender, "pending"])["result"])
    dup_raw = "0x" + sign_transfer(Account.create().address, 1_000_000, nonce)
    resp = rpc.call("eth_sendRawTransactionBatch", [[dup_raw, dup_raw]])
    assert "result" in resp, f"dup batch failed: {resp}"
    res = resp["result"]
    assert res[0].get("hash") and res[1].get("error"), f"dup batch wrong: {res}"
    print(f"[4c] OK: first accepted, duplicate rejected ({res[1]['error'][:60]})")

    print("ALL FUNCTIONAL TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
