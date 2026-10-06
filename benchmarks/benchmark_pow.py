"""Benchmark harness: PoW scaling + validation throughput → benchmarks/results.json"""
import json, sys, time
sys.path.insert(0, "src")
from coin.chain import Blockchain, find_block
from coin.utxo import get_coinbase_transaction
from coin.wallet import generate_private_key, get_public_key

out = {"pow": {}, "validation": {}}
addr = get_public_key(generate_private_key())
for d in (1, 2, 3):
    t0 = time.time()
    b = find_block(99, "x" * 64, int(time.time()), [get_coinbase_transaction(addr, 99)], d)
    out["pow"][str(d)] = {"nonce": b.nonce, "sec": round(time.time() - t0, 3)}
bc = Blockchain(addr)
for _ in range(3):
    bc.mine_next()
t0 = time.time()
ok = bc.is_valid_chain(bc.chain) is not None
out["validation"] = {"blocks": len(bc.chain), "sec": round(time.time() - t0, 4), "valid": ok}
with open("benchmarks/results.json", "w") as f:
    json.dump(out, f, indent=2)
print(json.dumps(out, indent=2))
