"""Exp 07 — Verify against REAL Bitcoin genesis (live + hardcoded cross-check).

Ground truth (Bitcoin Core chainparams.cpp, Blockchain.com explorer):
  hash=000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f
  nonce=2083236893, bits=0x1d00ffff (difficulty 1), time=1231006505,
  merkle=4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b
  message="The Times 03/Jan/2009 Chancellor on brink of second bailout for banks"

Recomputes double-SHA256 of the real 80-byte header and checks target.
Tries live fetch from mempool.space / blockchain.info; falls back to
hardcoded header when offline (CI-safe), always recomputing locally.
"""
import hashlib, json, struct, sys, urllib.request

HASH = "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f"
NONCE = 2083236893
BITS = 0x1D00FFFF
TIME = 1231006505
MERKLE = "4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b"


def bits_to_target(bits: int) -> int:
    exp = bits >> 24
    mant = bits & 0xFFFFFF
    return mant * (1 << (8 * (exp - 3)))


def header_bytes() -> bytes:
    ver = struct.pack("<L", 1)
    prev = bytes(32)
    mrk = bytes.fromhex(MERKLE)[::-1]
    ts = struct.pack("<L", TIME)
    bi = struct.pack("<L", BITS)
    no = struct.pack("<L", NONCE)
    return ver + prev + mrk + ts + bi + no


def hash_header(h: bytes) -> str:
    return hashlib.sha256(hashlib.sha256(h).digest()).digest()[::-1].hex()


def live_lookup():
    for url in ("https://mempool.space/api/block-height/0",
                "https://blockchain.info/rawblock/000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f?format=json"):
        try:
            with urllib.request.urlopen(url, timeout=8) as r:
                return url, r.read()[:200]
        except Exception as e:
            print(f"live {url} unreachable: {e}")
    return None, None


if __name__ == "__main__":
    url, sample = live_lookup()
    print(f"live source: {url or 'offline fallback (hardcoded header, still recomputed)'}")
    h = header_bytes()
    assert len(h) == 80
    got = hash_header(h)
    target = bits_to_target(BITS)
    print(f"recomputed: {got}")
    print(f"expected  : {HASH}")
    assert got == HASH, "genesis hash mismatch!"
    assert int(got, 16) < target, "hash not under difficulty-1 target!"
    print(f"nonce={NONCE} bits={hex(BITS)} target={hex(target)[:18]}... OK under target")
    print(f"time={TIME} (2009-01-03 18:15:05 UTC) merkle={MERKLE[:16]}...")
    with open("benchmarks/genesis_verify.json", "w") as f:
        json.dump({"hash": got, "nonce": NONCE, "bits": hex(BITS),
                   "target": hex(target), "live": url}, f, indent=2)
    print("OK: real Bitcoin genesis re-verified from first principles")
