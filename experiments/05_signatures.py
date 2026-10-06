"""Exp 05 — Signatures: only owner can spend; tamper breaks sig; wrong key fails."""
import sys
sys.path.insert(0, "src")
from coin.chain import Blockchain
from coin.utxo import get_transaction_id, validate_transaction
from coin.wallet import generate_private_key, get_public_key, create_transaction, verify_signature

sk_a = generate_private_key()
sk_m = generate_private_key()  # Mallory
a = get_public_key(sk_a)
bc = Blockchain(a)
recv = get_public_key(generate_private_key())
tx = create_transaction(recv, 30, sk_a, bc.unspent, [])
print(f"valid sig verifies: {verify_signature(tx.tx_ins[0].signature, tx.id, a)}")
assert verify_signature(tx.tx_ins[0].signature, tx.id, a)
# Mallory rewrites "Alice pays Mallory 50" — she cannot forge Alice's sig
old = tx.tx_ins[0].signature
tx.tx_outs[0].address = get_public_key(sk_m)
tx.tx_outs[0].amount = 50
new_id = get_transaction_id(tx)
print(f"forged id {new_id[:16]}... verifies with old sig: {verify_signature(old, new_id, a)}")
assert not verify_signature(old, new_id, a)
assert not validate_transaction(tx, bc.unspent, verify_signature)
# Mallory signs with HER key on Alice's coin -> address mismatch -> create fails
try:
    create_transaction(recv, 30, sk_m, bc.unspent, [])
    print("FAIL: wrong-key spend created")
except ValueError as e:
    print(f"wrong-key spend blocked: {e}")
print("OK: signature security verified")
