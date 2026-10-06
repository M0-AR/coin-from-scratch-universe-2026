"""Generate docs/assets charts (verified by execution)."""
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

with open("benchmarks/pow_scaling.json") as f:
    pow_data = json.load(f)

diffs = sorted(int(k) for k in pow_data)
nonces = [pow_data[str(d)]["nonce"] for d in diffs]
secs = [pow_data[str(d)]["seconds"] for d in diffs]

fig, ax1 = plt.subplots(figsize=(8, 4.5))
ax1.set_title("Proof-of-Work cost: nonces vs difficulty (hex zeros)")
ax1.set_xlabel("difficulty (leading zero hex chars)")
ax1.set_ylabel("nonces tried (log scale)")
ax1.semilogy(diffs, nonces, "o-", linewidth=2, markersize=8, label="measured nonces")
theory = [16 ** d for d in diffs]
scale = nonces[0] / theory[0]
ax1.semilogy(diffs, [t * scale for t in theory], "--", label="theory ~16x per zero (scaled)")
for d, n, s in zip(diffs, nonces, secs):
    ax1.annotate(f"{n:,}\n{s}s", (d, n), textcoords="offset points", xytext=(0, 12), ha="center", fontsize=9)
ax1.legend()
ax1.grid(True, which="both", alpha=0.3)
fig.tight_layout()
fig.savefig("docs/assets/pow_scaling.png", dpi=150)
print("wrote docs/assets/pow_scaling.png")

# Confirmation security curve (Satoshi Table)
# Confirmation security curve (Satoshi §11 exact: Poisson + Gambler's Ruin)
import math

def satoshi_prob(q, z):
    if q >= 0.5:
        return 1.0
    p = 1 - q
    lam = z * (q / p)
    return 1 - sum(math.exp(-lam) * lam ** k / math.factorial(k) * (1 - (q / p) ** (z - k)) for k in range(z + 1))

fig2, ax2 = plt.subplots(figsize=(8, 4.5))
ax2.set_title("Double-spend success probability vs confirmations (Satoshi §11 exact)")
ax2.set_xlabel("confirmations z")
ax2.set_ylabel("P(attacker catches up) (log scale)")
for q, style in ((0.10, "o-"), (0.30, "s-")):
    zs = list(range(0, 11))
    probs = [satoshi_prob(q, z) for z in zs]
    ax2.semilogy(zs, probs, style, label=f"attacker {int(q*100)}%")
ax2.axhline(0.001, color="gray", linestyle=":", label="0.1% line (6 conf @10% is far below)")
ax2.legend()
ax2.grid(True, which="both", alpha=0.3)
fig2.tight_layout()
fig2.savefig("docs/assets/confirmations.png", dpi=150)
print("wrote docs/assets/confirmations.png")

# Banner (social preview / OG image replacement, pure matplotlib — no external shots)
fig3 = plt.figure(figsize=(12, 6))
fig3.patch.set_facecolor("#0b1020")
ax3 = fig3.add_axes([0, 0, 1, 1])
ax3.axis("off")
ax3.text(0.5, 0.62, "BUILD YOUR OWN COIN", ha="center", va="center", fontsize=44, weight="bold", color="white")
ax3.text(0.5, 0.48, "ledger  •  mining  •  wallets  •  network", ha="center", va="center", fontsize=20, color="#7dd3fc")
ax3.text(0.5, 0.36, "135-line core  •  live Bitcoin verification  •  Docker 3-node network", ha="center", va="center", fontsize=14, color="#a5b4fc")
ax3.text(0.5, 0.22, "Python  •  Flask  •  secp256k1  •  UTXO  •  proof-of-work", ha="center", va="center", fontsize=12, color="#64748b")
fig3.savefig("docs/assets/banner.png", dpi=150, facecolor=fig3.get_facecolor())
print("wrote docs/assets/banner.png")
