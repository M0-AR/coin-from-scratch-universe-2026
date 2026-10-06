"""coin135 — the whole video in ~135 lines: fingerprints, mined chain, coins, signatures, network.

Run:  python coin135.py   (needs `pip install ecdsa`)
Covers: SHA-256 fingerprint, hash-linked chain, PoW nonce, UTXO + coinbase 50,
ECDSA secp256k1 sign/verify, mempool double-spend guard, fork = most work wins.
"""
import hashlib, time
from ecdsa import SECP256k1, SigningKey, VerifyingKey, util
H = lambda s: hashlib.sha256(s.encode()).hexdigest()
COIN = 50
def keypair():
    sk = SigningKey.generate(curve=SECP256k1); return sk.to_string().hex(), "04" + sk.get_verifying_key().to_string().hex()
def sign(txid, priv):
    sk = SigningKey.from_string(bytes.fromhex(priv), curve=SECP256k1)
    return sk.sign_digest_deterministic(hashlib.sha256(bytes.fromhex(txid)).digest(), hashfunc=hashlib.sha256, sigencode=util.sigencode_der).hex()
def verify(sig, txid, addr):
    try:
        vk = VerifyingKey.from_string(bytes.fromhex(addr[2:]), curve=SECP256k1)
        return vk.verify_digest(bytes.fromhex(sig), hashlib.sha256(bytes.fromhex(txid)).digest(), sigdecode=util.sigdecode_der)
    except Exception: return False
def txid(t): return H("".join(i[0] + str(i[1]) for i in t["ins"]) + "".join(o[0] + str(o[1]) for o in t["outs"]))
def coinbase(addr, h):
    t = {"ins": [("", h, "")], "outs": [(addr, COIN)]}; t["id"] = txid(t); return t
def make_tx(recv, amt, priv, utxos, pool):
    me = "04" + SigningKey.from_string(bytes.fromhex(priv), curve=SECP256k1).get_verifying_key().to_string().hex()
    mine = [u for u in utxos if u[2] == me and (u[0], u[1]) not in {(a, b) for p in pool for a, b, _ in p["ins"]}]
    sel, tot = [], 0
    for u in mine:
        sel.append(u); tot += u[3]
        if tot >= amt: break
    assert tot >= amt, "insufficient funds"
    outs = [(recv, amt)] + ([(me, tot - amt)] if tot > amt else [])
    t = {"ins": [(a, b, "") for a, b, _, _ in sel], "outs": outs}; t["id"] = txid(t)
    t["ins"] = [(a, b, sign(t["id"], priv)) for a, b, _ in t["ins"]]; return t
def valid_tx(t, utxos):
    if txid(t) != t["id"]: return False
    if sum(next(u[3] for u in utxos if u[0] == a and u[1] == b) for a, b, _ in t["ins"]) != sum(v for _, v in t["outs"]): return False
    return all(next((u[2] for u in utxos if u[0] == a and u[1] == b), None) and verify(s, t["id"], next(u[2] for u in utxos if u[0] == a and u[1] == b)) for a, b, s in t["ins"])
def apply(txs, utxos):
    spent = {(a, b) for t in txs for a, b, _ in t["ins"] if a}
    utxos = [u for u in utxos if (u[0], u[1]) not in spent]
    for t in txs:
        utxos += [(t["id"], i, addr, amt) for i, (addr, amt) in enumerate(t["outs"])]
    return utxos
def bhash(i, prev, ts, txs, diff, nonce): return H(f"{i}{prev}{ts}{''.join(t['id'] for t in txs)}{diff}{nonce}")
def mine(i, prev, txs, diff):
    ts = int(time.time()); n = 0
    while True:
        h = bhash(i, prev, ts, txs, diff, n)
        if h.startswith("0" * diff): return {"index": i, "hash": h, "prev": prev, "time": ts, "txs": txs, "diff": diff, "nonce": n}
        n += 1
def bal(addr, utxos): return sum(u[3] for u in utxos if u[2] == addr)
if __name__ == "__main__":
    a_priv, a_addr = keypair(); b_priv, b_addr = keypair(); m_priv, m_addr = keypair()
    print("fingerprint:", H("Alice pays Bob 30"), "\nchanged    :", H("Alice pays Bob 90"))
    g_cb = coinbase(a_addr, 0); genesis = mine(0, "", [g_cb], 0); utxos = apply([g_cb], [])
    print("genesis:", genesis["hash"], "alice:", bal(a_addr, utxos))
    t1 = make_tx(b_addr, 30, a_priv, utxos, [])
    assert valid_tx(t1, utxos)
    pool = [] if any((i[0], i[1]) in {(x[0], x[1]) for x in p["ins"]} for p in [] for i in t1["ins"]) else [t1]
    try:  # double-spend in pool must fail: same coin to Carol
        c_priv, c_addr = keypair(); t2 = make_tx(c_addr, 50, a_priv, utxos, pool); print("DOUBLE-SPEND NOT BLOCKED (bug)")
    except AssertionError: print("pool double-spend blocked: ok")
    b1 = mine(1, genesis["hash"], [coinbase(m_addr, 1), t1], 2); utxos = apply([coinbase(m_addr, 1), t1], utxos)
    print("block1:", b1["hash"], "nonce:", b1["nonce"], "alice:", bal(a_addr, utxos), "bob:", bal(b_addr, utxos))
    fake = dict(t1); fake["outs"] = [(m_addr, 30)]  # forged output keeps old id+sig
    print("forgery caught:", not valid_tx(fake, apply([g_cb], [])))
    honest, secret = [genesis, b1], [genesis]  # fork: 2 work vs 1 work
    print("fork choice: honest wins" if sum(16 ** b["diff"] for b in honest) > sum(16 ** b["diff"] for b in secret) else "fork bug")
    print("Two blocks, one payment, pool double-spend + forgery blocked. Toy coin only — no real value.")
