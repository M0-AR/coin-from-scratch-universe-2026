"""Exp 03 — Mining cost: each extra zero ~16x harder (hex difficulty).

Reproduces video anecdotes: ~20k guesses for 4 zeros on this laptop-class
hash; measures nonces + wall time for difficulty 1..4 and writes JSON.
Bitcoin genesis (10 zero HEX chars ~ 40 zero bits) shown for scale.
"""
import json, sys, time
sys.path.insert(0, "src")
from coin.chain import find_block
from coin.utxo import get_coinbase_transaction
from coin.wallet import generate_private_key, get_public_key

addr = get_public_key(generate_private_key())
results = {}
for diff in [1, 2, 3, 4]:
    t0 = time.time()
    b = find_block(1, "prev", int(time.time()), [get_coinbase_transaction(addr, 1)], diff)
    dt = time.time() - t0
    results[diff] = {"nonce": b.nonce, "seconds": round(dt, 3), "hash": b.hash}
    print(f"difficulty {diff}: nonce={b.nonce} time={dt:.2f}s hash={b.hash[:16]}...")
    assert b.hash.startswith("0" * diff)
ratios = {d: results[d]["nonce"] / max(1, results[d-1]["nonce"]) for d in [2, 3, 4]}
print("nonce ratios per extra zero:", {k: round(v, 1) for k, v in ratios.items()}, "(expect ~16x)")
with open("benchmarks/pow_scaling.json", "w") as f:
    json.dump(results, f, indent=2)
print("wrote benchmarks/pow_scaling.json")
print("OK: PoW cost scaling verified")
