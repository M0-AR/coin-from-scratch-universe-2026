"""Part 4 — Signatures (secp256k1, same curve as Bitcoin).

private_key: 256-bit secret (64 hex chars).
public_key / address: uncompressed point 04||X||Y (130 hex chars).
sign(tx.id) with private key; anyone verifies with address only.
Changing 1 char of the tx changes tx.id -> signature fails.
Spending someone else's coin with your key fails.

Uses the audited `ecdsa` package (RFC6979 deterministic k) — the <40 lines
of math the video refers to are exactly: keygen, ECDH multiply G*k,
DER sign, verify. Pure-python fallback documented in paper §4.
"""
from __future__ import annotations

import binascii
import hashlib

from ecdsa import SECP256k1, SigningKey, VerifyingKey, util

from .utxo import (
    Transaction,
    TxIn,
    TxOut,
    UnspentTxOut,
    find_unspent,
    get_transaction_id,
)


def generate_private_key() -> str:
    return SigningKey.generate(curve=SECP256k1).to_string().hex()


def get_public_key(private_key_hex: str) -> str:
    sk = SigningKey.from_string(bytes.fromhex(private_key_hex), curve=SECP256k1)
    vk = sk.get_verifying_key()
    return "04" + vk.to_string().hex()


def sign_data(data_hex: str, private_key_hex: str) -> str:
    sk = SigningKey.from_string(bytes.fromhex(private_key_hex), curve=SECP256k1)
    digest = hashlib.sha256(bytes.fromhex(data_hex)).digest() if _is_hex(data_hex) else hashlib.sha256(data_hex.encode()).digest()
    # Sign the tx id bytes deterministically (RFC6979 inside ecdsa lib).
    msg = bytes.fromhex(data_hex) if _is_hex(data_hex) and len(data_hex) == 64 else data_hex.encode()
    return sk.sign_digest_deterministic(
        hashlib.sha256(msg).digest(), hashfunc=hashlib.sha256,
        sigencode=util.sigencode_der,
    ).hex()


def verify_signature(signature_hex: str, data_hex: str, address: str) -> bool:
    try:
        if not address.startswith("04") or len(address) != 130:
            return False
        vk = VerifyingKey.from_string(bytes.fromhex(address[2:]), curve=SECP256k1)
        sig = bytes.fromhex(signature_hex)
        msg = bytes.fromhex(data_hex) if _is_hex(data_hex) and len(data_hex) == 64 else data_hex.encode()
        digest = hashlib.sha256(msg).digest()
        return vk.verify_digest(sig, digest, sigdecode=util.sigdecode_der)
    except Exception:
        return False


def _is_hex(s: str) -> bool:
    try:
        bytes.fromhex(s)
        return True
    except Exception:
        return False


def sign_tx_in(
    tx: Transaction, tx_in_index: int, private_key: str, uxtos: list[UnspentTxOut]
) -> str:
    ti = tx.tx_ins[tx_in_index]
    ref = find_unspent(ti.tx_out_id, ti.tx_out_index, uxtos)
    if ref is None:
        raise ValueError("referenced UTXO not found")
    if get_public_key(private_key) != ref.address:
        raise ValueError("private key does not match referenced address")
    return sign_data(tx.id, private_key)


def get_balance(address: str, uxtos: list[UnspentTxOut]) -> int:
    return sum(u.amount for u in uxtos if u.address == address)


def create_transaction(
    receiver: str,
    amount: int,
    private_key: str,
    uxtos: list[UnspentTxOut],
    tx_pool: list[Transaction] | None = None,
) -> Transaction:
    from .utxo import is_valid_address

    if not is_valid_address(receiver):
        raise ValueError("invalid receiver address")
    if not isinstance(amount, int) or amount <= 0:
        raise ValueError("invalid amount")
    my_address = get_public_key(private_key)
    my_uxtos = [u for u in uxtos if u.address == my_address]
    # Exclude UTXOs already referenced by the pool (double-spend guard).
    if tx_pool:
        pooled = {(ti.tx_out_id, ti.tx_out_index) for t in tx_pool for ti in t.tx_ins}
        my_uxtos = [u for u in my_uxtos if (u.tx_out_id, u.tx_out_index) not in pooled]
    current = 0
    included: list[UnspentTxOut] = []
    for u in my_uxtos:
        included.append(u)
        current += u.amount
        if current >= amount:
            break
    if current < amount:
        raise ValueError(f"not enough coins: have {current}, need {amount}")
    left_over = current - amount
    unsigned = [TxIn(tx_out_id=u.tx_out_id, tx_out_index=u.tx_out_index) for u in included]
    outs = [TxOut(address=receiver, amount=amount)]
    if left_over > 0:
        outs.append(TxOut(address=my_address, amount=left_over))
    tx = Transaction(tx_ins=unsigned, tx_outs=outs)
    tx.id = get_transaction_id(tx)
    for i in range(len(tx.tx_ins)):
        tx.tx_ins[i].signature = sign_tx_in(tx, i, private_key, uxtos)
    return tx
