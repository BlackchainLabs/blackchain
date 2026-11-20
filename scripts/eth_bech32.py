#!/usr/bin/env python3
"""Derive the black-prefixed bech32 address of an ethsecp256k1 key.

Usage: eth_bech32.py <home-dir> <key-name>
Prints the bech32 address to stdout and the 0x ETH address to stderr.
Reads the public key via `blackchaind keys show` (no private key involved).
"""
import base64
import json
import subprocess
import sys

BIN = "/home/hatch/workspace/blackchain/build/blackchaind-sdk54-bkc"


def main():
    home, name = sys.argv[1], sys.argv[2]
    out = subprocess.check_output(
        [BIN, "keys", "show", name, "--keyring-backend", "test",
         "--home", home, "--output", "json"])
    d = json.loads(out)
    pub = base64.b64decode(json.loads(d["pubkey"])["key"])
    from eth_hash.auto import keccak
    P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
    prefix, x = pub[0], int.from_bytes(pub[1:], "big")
    y = pow((pow(x, 3, P) + 7) % P, (P + 1) // 4, P)
    if (y % 2 == 0) != (prefix == 0x02):
        y = P - y
    eth = keccak(x.to_bytes(32, "big") + y.to_bytes(32, "big")).hex()[-40:]

    CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"

    def polymod(values):
        GEN = [0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3]
        chk = 1
        for v in values:
            b = chk >> 25
            chk = (chk & 0x1FFFFFF) << 5 ^ v
            for i in range(5):
                chk ^= GEN[i] if ((b >> i) & 1) else 0
        return chk

    def hrp_expand(hrp):
        return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]

    def convertbits(data, frombits, tobits, pad=True):
        acc, bits, ret = 0, 0, []
        maxv = (1 << tobits) - 1
        for value in data:
            acc = (acc << frombits) | value
            bits += frombits
            while bits >= tobits:
                bits -= tobits
                ret.append((acc >> bits) & maxv)
        if pad and bits:
            ret.append((acc << (tobits - bits)) & maxv)
        return ret

    data = convertbits(list(bytes.fromhex(eth)), 8, 5)
    values = hrp_expand("black") + data
    pm = polymod(values + [0, 0, 0, 0, 0, 0]) ^ 1
    cs = [(pm >> 5 * (5 - i)) & 31 for i in range(6)]
    print("black1" + "".join(CHARSET[d] for d in data + cs))
    print("ETH=0x" + eth, file=sys.stderr)


if __name__ == "__main__":
    main()
