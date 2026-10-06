"""Exp 06 — Forks: two miners, same height; most-work chain wins; attacker needs 51%.

Honest chain (2 blocks work) vs Mallory's secret branch (1 block), then the
exact Satoshi §11 double-spend probability (Poisson pre-mine + Gambler's Ruin
catch-up). Win prob collapses with confirmations — why 6 conf is convention.
"""
import math
import sys
sys.path.insert(0, "src")
from coin.chain import Blockchain, get_accumulated_difficulty
from coin.wallet import generate_private_key, get_public_key

a = get_public_key(generate_private_key())
honest, secret = Blockchain(a), Blockchain(a)
honest.mine_next(); honest.mine_next()
secret.mine_next()
wh, ws = get_accumulated_difficulty(honest.chain), get_accumulated_difficulty(secret.chain)
print(f"honest work={wh} (len {len(honest.chain)}); attacker work={ws} (len {len(secret.chain)})")
assert wh > ws and not honest.replace_chain(secret.chain)
print("honest nodes ignore lighter fork: OK")


def satoshi_prob(q: float, z: int) -> float:
    """Whitepaper §11 exact probability the attacker ever catches up from z behind.

    Poisson(λ=z·q/p) blocks pre-mined during confirmation, then (q/p)^(z-k)
    Gambler's Ruin from the remaining gap. P=1 for q>=0.5.
    """
    if q >= 0.5:
        return 1.0
    p = 1 - q
    lam = z * (q / p)
    hidden = 0.0
    for k in range(z + 1):
        poisson = math.exp(-lam) * lam ** k / math.factorial(k)
        hidden += poisson * (1 - (q / p) ** (z - k))
    return 1 - hidden


for q in (0.10, 0.30):
    row = {z: round(satoshi_prob(q, z), 7) for z in (1, 2, 3, 6)}
    print(f"q={q}: P(success|z) = {row}")
# Whitepaper §11 reference values (bitcoin.org/bitcoin.pdf, §11):
assert abs(satoshi_prob(0.10, 5) - 0.0009137) < 1e-7
assert abs(satoshi_prob(0.10, 6) - 0.0002428) < 1e-7
assert abs(satoshi_prob(0.30, 5) - 0.1773523) < 1e-7
assert abs(satoshi_prob(0.30, 6) - 0.1321112) < 1e-7
print("OK: Satoshi §11 table reproduced (6 conf = 0.024% at q=10%, 13.2% at q=30%)")
