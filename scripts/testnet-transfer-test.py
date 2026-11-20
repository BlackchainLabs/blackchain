#!/usr/bin/env python3
"""EVM transfer test on the 3-validator testnet rehearsal (Sesi 8).

- Exports the val1 validator key IN MEMORY via `blackchaind keys export
  --unarmored-hex` (testnet key, no value). The private key is NEVER
  printed, logged, or written to disk.
- Sends 1,000,000 wei from the val1 validator ETH address to a fresh
  one-time recipient, then verifies the receipt + balances on ALL THREE
  EVM endpoints (proof the tx replicated across the network).

Usage: testnet-transfer-test.py --home <val1-home> --rpc <val1-evm-url>
       --check-rpcs <url1,url2,url3>
"""
import argparse
import json
import subprocess
import sys
import time
import urllib.request

from eth_account import Account

BIN = "/home/hatch/workspace/blackchain/build/blackchaind-sdk54-bkc"


def rpc_call(url, method, params=None):
    body = json.dumps(
        {"jsonrpc": "2.0", "method": method, "params": params or [], "id": 1}
    ).encode()
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        out = json.load(r)
    if "error" in out:
        raise RuntimeError(f"{method} -> {out['error']}")
    return out["result"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--home", required=True)
    ap.add_argument("--rpc", required=True)
    ap.add_argument("--check-rpcs", required=True)
    ap.add_argument("--value", type=int, default=1_000_000)
    args = ap.parse_args()

    chain_id = int(rpc_call(args.rpc, "eth_chainId"), 16)
    assert chain_id == 20261120, f"chainId mismatch: {chain_id}"

    # Private key stays in memory only.
    pk_hex = subprocess.check_output(
        [BIN, "keys", "export", "validator", "--keyring-backend", "test",
         "--home", args.home, "--unarmored-hex", "--unsafe", "-y"],
        stderr=subprocess.DEVNULL).decode().strip()
    sender = Account.from_key(pk_hex)
    recipient = Account.create()
    print(f"sender:    {sender.address}")
    print(f"recipient: {recipient.address} (one-time)")
    bal_before = int(rpc_call(args.rpc, "eth_getBalance",
                              [sender.address, "latest"]), 16)
    print(f"sender balance before: {bal_before} wei")
    nonce = int(rpc_call(args.rpc, "eth_getTransactionCount",
                         [sender.address, "pending"]), 16)
    gas_price = int(rpc_call(args.rpc, "eth_gasPrice"), 16)
    tx = {"to": recipient.address, "value": args.value, "gas": 21000,
          "gasPrice": gas_price, "nonce": nonce, "chainId": chain_id}
    signed = sender.sign_transaction(tx)
    tx_hash = rpc_call(args.rpc, "eth_sendRawTransaction",
                       ["0x" + signed.raw_transaction.hex()])
    print(f"tx hash: {tx_hash}")

    receipt = None
    for _ in range(60):
        receipt = rpc_call(args.rpc, "eth_getTransactionReceipt", [tx_hash])
        if receipt:
            break
        time.sleep(1)
    assert receipt, "no receipt within 60s"
    print(f"receipt: block {int(receipt['blockNumber'], 16)}, "
          f"status {receipt['status']}, gasUsed "
          f"{int(receipt['gasUsed'], 16)}")
    assert receipt["status"] == "0x1", "receipt status != success"
    bal_after = int(rpc_call(args.rpc, "eth_getBalance",
                             [sender.address, "latest"]), 16)
    recv_bal = int(rpc_call(args.rpc, "eth_getBalance",
                            [recipient.address, "latest"]), 16)
    print(f"sender balance after:  {bal_after} wei "
          f"(delta {bal_after - bal_before})")
    print(f"recipient balance:     {recv_bal} wei "
          f"(expected +{args.value})")
    assert recv_bal == args.value, "recipient balance mismatch"
    assert bal_after - bal_before == -(args.value + 21000 * gas_price), \
        "sender delta mismatch (value + gas)"

    # Verify the same receipt + recipient balance on every node.
    for url in args.check_rpcs.split(","):
        r2 = rpc_call(url, "eth_getTransactionReceipt", [tx_hash])
        b2 = int(rpc_call(url, "eth_getBalance",
                          [recipient.address, "latest"]), 16)
        bn = int(rpc_call(url, "eth_blockNumber"), 16)
        print(f"{url}: receipt block {int(r2['blockNumber'], 16)}, "
              f"status {r2['status']}, recipient {b2} wei, "
              f"blockNumber {bn}")
        assert r2["status"] == "0x1" and b2 == args.value
    print(f"TRANSFER OK on all {len(args.check_rpcs.split(','))} nodes")


if __name__ == "__main__":
    main()
