"""Part 3 — Coins as UTXOs (no account balances stored anywhere).

Every coin is an *output* of a transaction: (amount -> address).
New coins: coinbase tx (first tx in every block) pays miner COINBASE_AMOUNT.
Spend: consume whole UTXOs (like breaking a banknote), create new outputs
(payment + change). inputs_sum == outputs_sum. Balance = sum(unspent for you).

Directly follows Naivecoin chapter 3 + Bitcoin developer guide semantics,
simplified: address = uncompressed secp256k1 public key (04||X||Y, 130 hex).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .hashutil import sha256_hex

COINBASE_AMOUNT = 50


@dataclass
class TxIn:
    tx_out_id: str = ""
    tx_out_index: int = 0
    signature: str = ""


@dataclass
class TxOut:
    address: str = ""
    amount: int = 0


@dataclass
class Transaction:
    id: str = ""
    tx_ins: list[TxIn] = field(default_factory=list)
    tx_outs: list[TxOut] = field(default_factory=list)


@dataclass
class UnspentTxOut:
    tx_out_id: str = ""
    tx_out_index: int = 0
    address: str = ""
    amount: int = 0


def get_transaction_id(tx: Transaction) -> str:
    tx_in_content = "".join(ti.tx_out_id + str(ti.tx_out_index) for ti in tx.tx_ins)
    tx_out_content = "".join(to.address + str(to.amount) for to in tx.tx_outs)
    return sha256_hex(tx_in_content + tx_out_content)


def is_valid_address(address: str) -> bool:
    if len(address) != 130:
        return False
    if not all(c in "0123456789abcdefABCDEF" for c in address):
        return False
    return address.startswith("04")


def find_unspent(tx_out_id: str, index: int, uxtos: list[UnspentTxOut]) -> UnspentTxOut | None:
    for u in uxtos:
        if u.tx_out_id == tx_out_id and u.tx_out_index == index:
            return u
    return None


def get_tx_in_amount(tx_in: TxIn, uxtos: list[UnspentTxOut]) -> int:
    found = find_unspent(tx_in.tx_out_id, tx_in.tx_out_index, uxtos)
    if found is None:
        raise ValueError("referenced UTXO not found")
    return found.amount


def validate_coinbase(tx: Transaction, block_index: int) -> bool:
    if tx is None:
        return False
    if get_transaction_id(tx) != tx.id:
        return False
    if len(tx.tx_ins) != 1:
        return False
    if tx.tx_ins[0].tx_out_index != block_index:
        return False
    if len(tx.tx_outs) != 1:
        return False
    if tx.tx_outs[0].amount != COINBASE_AMOUNT:
        return False
    return True


def _has_duplicates(tx_ins: list[TxIn]) -> bool:
    seen: set[str] = set()
    for ti in tx_ins:
        key = ti.tx_out_id + ":" + str(ti.tx_out_index)
        if key in seen:
            return True
        seen.add(key)
    return False


def validate_transaction(tx: Transaction, uxtos: list[UnspentTxOut], verify_sig) -> bool:
    """verify_sig(signature_hex, tx_id, address) -> bool (injected from wallet)."""
    if get_transaction_id(tx) != tx.id:
        return False
    for ti in tx.tx_ins:
        ref = find_unspent(ti.tx_out_id, ti.tx_out_index, uxtos)
        if ref is None:
            return False
        if not verify_sig(ti.signature, tx.id, ref.address):
            return False
    total_in = sum(get_tx_in_amount(ti, uxtos) for ti in tx.tx_ins)
    total_out = sum(to.amount for to in tx.tx_outs)
    if total_out != total_in:
        return False
    return True


def validate_block_transactions(
    txs: list[Transaction], uxtos: list[UnspentTxOut], block_index: int, verify_sig
) -> bool:
    if not txs:
        return False
    if not validate_coinbase(txs[0], block_index):
        return False
    all_ins: list[TxIn] = []
    for t in txs:
        all_ins.extend(t.tx_ins)
    # coinbase input is synthetic ("", block_index) — exclude from dup check
    normal_ins = [ti for t in txs[1:] for ti in t.tx_ins]
    if _has_duplicates(normal_ins):
        return False
    # coinbase input must not collide with real spends either
    if _has_duplicates([ti for t in txs for ti in t.tx_ins if ti.tx_out_id != ""]):
        return False
    for t in txs[1:]:
        if not validate_transaction(t, uxtos, verify_sig):
            return False
    void = [ti for ti in normal_ins if ti.tx_out_id == ""]
    if void:
        return False
    return True


def get_coinbase_transaction(address: str, block_index: int) -> Transaction:
    tx = Transaction()
    tx.tx_ins = [TxIn(tx_out_id="", tx_out_index=block_index, signature="")]
    tx.tx_outs = [TxOut(address=address, amount=COINBASE_AMOUNT)]
    tx.id = get_transaction_id(tx)
    return tx


def update_unspent(
    new_txs: list[Transaction], uxtos: list[UnspentTxOut]
) -> list[UnspentTxOut]:
    new_uxtos: list[UnspentTxOut] = []
    for t in new_txs:
        for idx, to in enumerate(t.tx_outs):
            new_uxtos.append(UnspentTxOut(t.id, idx, to.address, to.amount))
    consumed = {(ti.tx_out_id, ti.tx_out_index) for t in new_txs for ti in t.tx_ins}
    remaining = [u for u in uxtos if (u.tx_out_id, u.tx_out_index) not in consumed]
    return remaining + new_uxtos


def process_transactions(
    txs: list[Transaction], uxtos: list[UnspentTxOut], block_index: int, verify_sig
) -> list[UnspentTxOut] | None:
    if not validate_block_transactions(txs, uxtos, block_index, verify_sig):
        return None
    return update_unspent(txs, uxtos)
