"""Exp 04 — UTXO + double-spend: pool rejects 2nd spend; block rejects dup inputs."""
import sys
sys.path.insert(0, "src")
from coin.chain import Blockchain, find_block, get_difficulty
from coin.utxo import get_coinbase_transaction
from coin.wallet import generate_private_key, get_public_key, create_transaction, get_balance
import time

sk_a, sk_b, sk_c = generate_private_key(), generate_private_key(), generate_private_key()
a, b, c = get_public_key(sk_a), get_public_key(sk_b), get_public_key(sk_c)
bc = Blockchain(a)
print(f"genesis: alice={get_balance(a, bc.unspent)} (coinbase 50)")
t1 = create_transaction(b, 30, sk_a, bc.unspent, [])
print(f"alice->bob 30 (change 20 back). tx {t1.id[:16]}...")
assert bc.add_transaction_to_pool(t1)
try:
    t2 = create_transaction(c, 50, sk_a, bc.unspent, bc.tx_pool)
    print("FAIL: pool double-spend accepted")
except ValueError as e:
    print(f"pool double-spend rejected: {e}")
blk = bc.mine_block_with([t1])
print(f"block {blk.index} mined nonce={blk.nonce}; alice={get_balance(a, bc.unspent)} bob={get_balance(b, bc.unspent)}")
assert get_balance(b, bc.unspent) == 30
# duplicate inputs inside one block must be rejected
prev = bc.latest()
diff = get_difficulty(bc.chain)
t3 = create_transaction(c, 5, sk_b, bc.unspent, [])
cb = get_coinbase_transaction(bc.miner_address, prev.index + 1)
evil = find_block(prev.index + 1, prev.hash, int(time.time()), [cb, t3, t3], diff)
assert not bc.add_block(evil), "dup-input block accepted!"
print("OK: in-block double-spend rejected")
