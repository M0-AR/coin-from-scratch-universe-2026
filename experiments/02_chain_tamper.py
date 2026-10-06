"""Exp 02 — Chain: tamper breaks hash link; full verification is one loop."""
import sys
sys.path.insert(0, "src")
from coin.chain import Blockchain, calculate_hash_for_block
from coin.wallet import generate_private_key, get_public_key

bc = Blockchain(get_public_key(generate_private_key()))
bc.mine_next()
print(f"chain length {len(bc.chain)}; tip {bc.latest().hash[:16]}...")
# honest verify
for i in range(1, len(bc.chain)):
    assert bc.chain[i].previous_hash == bc.chain[i-1].hash
    assert calculate_hash_for_block(bc.chain[i]) == bc.chain[i].hash
print("honest chain links: OK")
# cheat: block 0 reward 50 -> 5000
bc.chain[0].data[0].tx_outs[0].amount = 5000
broken_hash = calculate_hash_for_block(bc.chain[0]) != bc.chain[0].hash
broken_link = bc.chain[1].previous_hash != calculate_hash_for_block(bc.chain[0])
print(f"tampered hash mismatch: {broken_hash}; next link broken: {broken_link}")
assert broken_hash and broken_link
print("OK: tamper-evidence verified (recompute-all needed -> PoW makes it expensive)")
