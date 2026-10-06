"""Part 5 — Network node (Flask HTTP API + simple HTTP P2P broadcast).

Naivecoin uses WebSockets; we use plain HTTP POST/GET via `requests` so the
whole network runs with Flask only (documented simplification, same rules):
  * every node keeps its own full copy of the chain,
  * new transactions / blocks are broadcast to every peer,
  * fork choice = valid chain with most total work; next block breaks ties.

Endpoints (Naivecoin-compatible + dvf-compatible aliases):
  GET  /blocks, /chain, /transactionPool, /peers, /balance?address=, /address/<a>
  POST /mineBlock, /mine, /sendTransaction, /transactions/new,
       /mineTransaction, /addPeer, /nodes/register, /nodes/resolve
"""
from __future__ import annotations

import argparse
import json
import os
import threading

import requests
from flask import Flask, jsonify, request

from .chain import Block, Blockchain
from .utxo import Transaction, TxIn, TxOut, is_valid_address

# --- wallet imports (kept explicit for readability) ---
from .wallet import create_transaction as _create_tx
from .wallet import generate_private_key as _gen_key
from .wallet import get_balance as _get_balance
from .wallet import get_public_key as _get_pub

PEERS: set[str] = set()
CHAIN: Blockchain | None = None
PRIVATE_KEY: str = ""
ADDRESS: str = ""

app = Flask(__name__)


def init_node(miner_key: str | None = None) -> Blockchain:
    global CHAIN, PRIVATE_KEY, ADDRESS
    PRIVATE_KEY = miner_key or os.environ.get("COIN_PRIVATE_KEY") or _gen_key()
    ADDRESS = _get_pub(PRIVATE_KEY)
    CHAIN = Blockchain(ADDRESS)
    return CHAIN


def _broadcast(path: str, payload: dict) -> None:
    for peer in list(PEERS):
        try:
            requests.post(peer.rstrip("/") + path, json=payload, timeout=3)
        except Exception:
            pass


@app.get("/blocks")
@app.get("/chain")
def blocks():
    assert CHAIN is not None
    return jsonify([b.to_dict() for b in CHAIN.chain])


@app.get("/transactionPool")
def pool():
    assert CHAIN is not None
    out = [{"id": t.id,
            "txIns": [{"txOutId": i.tx_out_id, "txOutIndex": i.tx_out_index, "signature": i.signature} for i in t.tx_ins],
            "txOuts": [{"address": o.address, "amount": o.amount} for o in t.tx_outs]} for t in CHAIN.tx_pool]
    return jsonify(out)


@app.get("/peers")
def peers():
    return jsonify(sorted(PEERS))


@app.post("/mineBlock")
@app.post("/mine")
def mine_block():
    assert CHAIN is not None
    b = CHAIN.mine_next()
    _broadcast("/receiveBlock", {"block": b.to_dict()})
    return jsonify(b.to_dict()), 201


@app.post("/mineTransaction")
def mine_transaction():
    assert CHAIN is not None
    data = request.get_json(force=True)
    tx = _create_tx(data["address"], data["amount"], PRIVATE_KEY, CHAIN.unspent, CHAIN.tx_pool)
    b = CHAIN.mine_block_with([tx])
    _broadcast("/receiveBlock", {"block": b.to_dict()})
    return jsonify(b.to_dict()), 201


@app.post("/sendTransaction")
@app.post("/transactions/new")
def send_tx():
    assert CHAIN is not None
    data = request.get_json(force=True)
    address = data.get("address", data.get("recipient"))
    amount = data.get("amount")
    sender_key = data.get("privateKey", PRIVATE_KEY)
    try:
        tx = _create_tx(address, amount, sender_key, CHAIN.unspent, CHAIN.tx_pool)
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    if not CHAIN.add_transaction_to_pool(tx):
        return jsonify({"error": "rejected: double-spend or invalid signature"}), 400
    _broadcast("/receiveTransaction", {"transaction": {
        "id": tx.id,
        "txIns": [{"txOutId": i.tx_out_id, "txOutIndex": i.tx_out_index, "signature": i.signature} for i in tx.tx_ins],
        "txOuts": [{"address": o.address, "amount": o.amount} for o in tx.tx_outs]}})
    return jsonify({"id": tx.id}), 201


@app.post("/receiveTransaction")
def receive_tx():
    assert CHAIN is not None
    d = request.get_json(force=True).get("transaction", request.get_json(force=True))
    tx = Transaction(id=d["id"],
                     tx_ins=[TxIn(i.get("txOutId", ""), i.get("txOutIndex", 0), i.get("signature", "")) for i in d.get("txIns", [])],
                     tx_outs=[TxOut(o.get("address", ""), o.get("amount", 0)) for o in d.get("txOuts", [])])
    ok = CHAIN.add_transaction_to_pool(tx)
    return jsonify({"accepted": ok}), 201 if ok else 400


@app.post("/receiveBlock")
def receive_block():
    assert CHAIN is not None
    d = request.get_json(force=True).get("block", request.get_json(force=True))
    b = Block.from_dict(d)
    # fast path: extends tip
    if b.previous_hash == CHAIN.latest().hash and b.index == CHAIN.latest().index + 1:
        ok = CHAIN.add_block(b)
        return jsonify({"accepted": ok}), 201 if ok else 400
    # slow path: ask a peer for full chain (fork resolution)
    return jsonify({"accepted": False, "hint": "not tip; call /nodes/resolve"}), 202


@app.post("/addPeer")
@app.post("/nodes/register")
def add_peer():
    data = request.get_json(force=True)
    urls = data.get("peers", [data.get("peer", data.get("node", ""))])
    for u in urls:
        if u:
            PEERS.add(u.rstrip("/"))
    return jsonify(sorted(PEERS)), 201


@app.get("/nodes/resolve")
def resolve():
    assert CHAIN is not None
    best = None
    for peer in list(PEERS):
        try:
            r = requests.get(peer.rstrip("/") + "/blocks", timeout=5)
            if r.status_code != 200:
                continue
            chain = [Block.from_dict(d) for d in r.json()]
            if CHAIN.is_valid_chain(chain) is not None:
                from .chain import get_accumulated_difficulty
                if best is None or get_accumulated_difficulty(chain) > get_accumulated_difficulty(best):
                    best = chain
        except Exception:
            continue
    if best is not None and CHAIN.replace_chain(best):
        return jsonify({"replaced": True, "length": len(CHAIN.chain)})
    return jsonify({"replaced": False, "length": len(CHAIN.chain)})


@app.get("/balance")
def balance():
    assert CHAIN is not None
    addr = request.args.get("address", ADDRESS)
    return jsonify({"address": addr, "balance": _get_balance(addr, CHAIN.unspent)})


@app.get("/address/<addr>")
def address_info(addr: str):
    assert CHAIN is not None
    if not is_valid_address(addr):
        return jsonify({"error": "invalid address"}), 400
    return jsonify({"address": addr, "balance": _get_balance(addr, CHAIN.unspent),
                    "utxos": [{"txOutId": u.tx_out_id, "txOutIndex": u.tx_out_index, "amount": u.amount}
                              for u in CHAIN.unspent if u.address == addr]})


@app.get("/wallet")
def wallet_info():
    return jsonify({"address": ADDRESS, "note": "private key never served; set COIN_PRIVATE_KEY env"})


def main() -> None:
    ap = argparse.ArgumentParser(description="coin node (from-scratch cryptocurrency)")
    ap.add_argument("-p", "--port", type=int, default=int(os.environ.get("PORT", "3001")))
    ap.add_argument("--peer", action="append", default=[], help="peer base URL, e.g. http://node2:3001")
    ap.add_argument("--key", default=os.environ.get("COIN_PRIVATE_KEY"), help="hex private key (else random)")
    args = ap.parse_args()
    init_node(args.key)
    for p in args.peer:
        PEERS.add(p.rstrip("/"))
    print(f"node address={ADDRESS} port={args.port} peers={sorted(PEERS)}", flush=True)
    app.run(host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()
