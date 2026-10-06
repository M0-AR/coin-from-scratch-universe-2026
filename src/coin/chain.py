"""Part 2 + Part 5 — Mined chain + network consensus (longest total work).

Block = index, hash, previous_hash, timestamp, data (txs), difficulty, nonce.
Mining: iterate nonce until hash has `difficulty` leading zero HEX chars.
Each extra zero ~16x harder (measured in benchmarks/).

Retarget (Naivecoin rule, Bitcoin spirit):
  every DIFFICULTY_ADJUSTMENT_INTERVAL blocks, compare actual timespan vs
  expected (BLOCK_GENERATION_INTERVAL * interval); +1 / -1 / same.
Bitcoin uses 10 min + 2016 blocks; we default to 10 s + 10 blocks so forks
and retargets are observable on a laptop (configurable).

Fork choice: valid chain with greatest accumulated work wins,
  work(block) = 16^difficulty. Next block breaks ties.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from .hashutil import hash_matches_difficulty_hex, sha256_hex
from .utxo import Transaction, get_coinbase_transaction, process_transactions
from .wallet import verify_signature

BLOCK_GENERATION_INTERVAL = 10  # seconds (Naivecoin default; Bitcoin: 600)
DIFFICULTY_ADJUSTMENT_INTERVAL = 10  # blocks (Bitcoin: 2016)

GENESIS_TIMESTAMP = 1465154705
GENESIS_PREV = ""
GENESIS_DIFFICULTY = 0


@dataclass
class Block:
    index: int = 0
    hash: str = ""
    previous_hash: str = ""
    timestamp: int = 0
    data: list[Transaction] = field(default_factory=list)
    difficulty: int = 0
    nonce: int = 0

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "hash": self.hash,
            "previousHash": self.previous_hash,
            "timestamp": self.timestamp,
            "data": [
                {
                    "id": t.id,
                    "txIns": [
                        {"txOutId": ti.tx_out_id, "txOutIndex": ti.tx_out_index, "signature": ti.signature}
                        for ti in t.tx_ins
                    ],
                    "txOuts": [{"address": to.address, "amount": to.amount} for to in t.tx_outs],
                }
                for t in self.data
            ],
            "difficulty": self.difficulty,
            "nonce": self.nonce,
        }

    @staticmethod
    def from_dict(d: dict) -> "Block":
        from .utxo import TxIn, TxOut

        txs: list[Transaction] = []
        for td in d.get("data", []):
            txs.append(
                Transaction(
                    id=td.get("id", ""),
                    tx_ins=[TxIn(ti.get("txOutId", ""), ti.get("txOutIndex", 0), ti.get("signature", "")) for ti in td.get("txIns", [])],
                    tx_outs=[TxOut(to.get("address", ""), to.get("amount", 0)) for to in td.get("txOuts", [])],
                )
            )
        return Block(
            index=d["index"], hash=d["hash"], previous_hash=d.get("previousHash", d.get("previous_hash", "")),
            timestamp=d["timestamp"], data=txs, difficulty=d.get("difficulty", 0), nonce=d.get("nonce", 0),
        )


def calculate_hash(index: int, previous_hash: str, timestamp: int,
                   data: list[Transaction], difficulty: int, nonce: int) -> str:
    payload = f"{index}{previous_hash}{timestamp}{_txs_repr(data)}{difficulty}{nonce}"
    return sha256_hex(payload)


def _txs_repr(data: list[Transaction]) -> str:
    parts: list[str] = []
    for t in data:
        parts.append(t.id + "".join(ti.tx_out_id + str(ti.tx_out_index) for ti in t.tx_ins))
        parts.append("".join(to.address + str(to.amount) for to in t.tx_outs))
    return "".join(parts)


def calculate_hash_for_block(b: Block) -> str:
    return calculate_hash(b.index, b.previous_hash, b.timestamp, b.data, b.difficulty, b.nonce)


def hash_matches_block_content(b: Block) -> bool:
    return calculate_hash_for_block(b) == b.hash


def get_accumulated_difficulty(chain: list[Block]) -> int:
    return sum(16 ** b.difficulty for b in chain)


def make_genesis_block(miner_address: str) -> Block:
    from .utxo import get_transaction_id
    coinbase = get_coinbase_transaction(miner_address, 0)
    h = calculate_hash(0, GENESIS_PREV, GENESIS_TIMESTAMP, [coinbase], GENESIS_DIFFICULTY, 0)
    return Block(0, h, GENESIS_PREV, GENESIS_TIMESTAMP, [coinbase], GENESIS_DIFFICULTY, 0)


def is_valid_block_structure(b: Block) -> bool:
    return (
        isinstance(b.index, int)
        and isinstance(b.hash, str)
        and isinstance(b.previous_hash, str)
        and isinstance(b.timestamp, int)
        and isinstance(b.data, list)
        and isinstance(b.difficulty, int)
        and isinstance(b.nonce, int)
    )


def is_valid_timestamp(new_b: Block, prev_b: Block) -> bool:
    return (prev_b.timestamp - 60 < new_b.timestamp) and (new_b.timestamp - 60 < int(time.time()))


def has_valid_hash(b: Block) -> bool:
    if not hash_matches_block_content(b):
        return False
    if not hash_matches_difficulty_hex(b.hash, b.difficulty):
        return False
    return True


def is_valid_new_block(new_b: Block, prev_b: Block) -> bool:
    if not is_valid_block_structure(new_b):
        return False
    if prev_b.index + 1 != new_b.index:
        return False
    if prev_b.hash != new_b.previous_hash:
        return False
    if not is_valid_timestamp(new_b, prev_b):
        return False
    if not has_valid_hash(new_b):
        return False
    return True


def get_difficulty(chain: list[Block]) -> int:
    latest = chain[-1]
    if latest.index % DIFFICULTY_ADJUSTMENT_INTERVAL == 0 and latest.index != 0:
        return get_adjusted_difficulty(latest, chain)
    return latest.difficulty


def get_adjusted_difficulty(latest: Block, chain: list[Block]) -> int:
    prev_adj = chain[max(0, len(chain) - DIFFICULTY_ADJUSTMENT_INTERVAL)]
    expected = BLOCK_GENERATION_INTERVAL * DIFFICULTY_ADJUSTMENT_INTERVAL
    taken = latest.timestamp - prev_adj.timestamp
    if taken < expected / 2:
        return prev_adj.difficulty + 1
    if taken > expected * 2:
        return max(0, prev_adj.difficulty - 1)
    return prev_adj.difficulty


def find_block(index: int, previous_hash: str, timestamp: int,
               data: list[Transaction], difficulty: int) -> Block:
    nonce = 0
    while True:
        h = calculate_hash(index, previous_hash, timestamp, data, difficulty, nonce)
        if hash_matches_difficulty_hex(h, difficulty):
            return Block(index, h, previous_hash, timestamp, data, difficulty, nonce)
        nonce += 1


class Blockchain:
    """Single node's full copy: chain + UTXO set + mempool."""

    def __init__(self, miner_address: str):
        from .utxo import UnspentTxOut
        genesis = make_genesis_block(miner_address)
        self.chain: list[Block] = [genesis]
        self.unspent: list[UnspentTxOut] = process_transactions(
            genesis.data, [], 0, verify_signature
        ) or []
        self.tx_pool: list[Transaction] = []
        self.miner_address = miner_address

    def latest(self) -> Block:
        return self.chain[-1]

    def mine_block_with(self, txs: list[Transaction]) -> Block:
        prev = self.latest()
        difficulty = get_difficulty(self.chain)
        coinbase = get_coinbase_transaction(self.miner_address, prev.index + 1)
        block_data = [coinbase] + txs
        new_block = find_block(prev.index + 1, prev.hash, int(time.time()), block_data, difficulty)
        if self.add_block(new_block):
            return new_block
        raise RuntimeError("mined block rejected (invalid transactions?)")

    def mine_empty(self) -> Block:
        return self.mine_block_with(list(self.tx_pool)[:0] if False else [])

    def mine_next(self) -> Block:
        """Mine coinbase + entire pool (Naivecoin generateNextBlock)."""
        block = self.mine_block_with(list(self.tx_pool))
        return block

    def add_block(self, b: Block) -> bool:
        if not is_valid_new_block(b, self.latest()):
            return False
        new_uxto = process_transactions(b.data, self.unspent, b.index, verify_signature)
        if new_uxto is None:
            return False
        self.chain.append(b)
        self.unspent = new_uxto
        self._update_pool()
        return True

    def add_transaction_to_pool(self, tx) -> bool:
        from .utxo import validate_transaction
        if not validate_transaction(tx, self.unspent, verify_signature):
            return False
        # pool-level double-spend: input already referenced in pool?
        pooled = {(ti.tx_out_id, ti.tx_out_index) for t in self.tx_pool for ti in t.tx_ins}
        for ti in tx.tx_ins:
            if (ti.tx_out_id, ti.tx_out_index) in pooled:
                return False
        self.tx_pool.append(tx)
        return True

    def _update_pool(self) -> None:
        valid: list[Transaction] = []
        for tx in self.tx_pool:
            # drop txs whose inputs got spent by the new block
            from .utxo import validate_transaction
            if validate_transaction(tx, self.unspent, verify_signature):
                valid.append(tx)
        # also drop double-refs within remaining pool
        seen: set[tuple[str, int]] = set()
        deduped: list[Transaction] = []
        for tx in valid:
            keys = [(ti.tx_out_id, ti.tx_out_index) for ti in tx.tx_ins]
            if any(k in seen for k in keys):
                continue
            seen.update(keys)
            deduped.append(tx)
        self.tx_pool = deduped

    def is_valid_chain(self, chain: list[Block]) -> list | None:
        from .utxo import UnspentTxOut
        genesis = self.chain[0]
        if chain[0].to_dict() != genesis.to_dict():
            return None
        uxtos: list[UnspentTxOut] = []
        for i, b in enumerate(chain):
            if i != 0 and not is_valid_new_block(b, chain[i - 1]):
                return None
            uxtos = process_transactions(b.data, uxtos, b.index, verify_signature)
            if uxtos is None:
                return None
        return uxtos

    def replace_chain(self, new_chain: list[Block]) -> bool:
        uxtos = self.is_valid_chain(new_chain)
        if uxtos is None:
            return False
        if get_accumulated_difficulty(new_chain) > get_accumulated_difficulty(self.chain):
            self.chain = new_chain
            self.unspent = uxtos
            self._update_pool()
            return True
        return False
