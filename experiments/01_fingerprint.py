"""Exp 01 — Fingerprint: SHA-256 avalanche + irreversibility demo."""
import sys
sys.path.insert(0, "src")
from coin.hashutil import sha256_hex, hamming_distance_hex, hex_to_binary

a = sha256_hex("Alice pays Bob 30")
b = sha256_hex("Alice pays Bob 90")
print(f"Alice pays Bob 30 -> {a}")
print(f"Alice pays Bob 90 -> {b}")
d = hamming_distance_hex(a, b)
print(f"bit flips: {d}/256 = {d/256:.1%} (ideal avalanche ~50%)")
print(f"len: {len(a)} hex chars; one-way: cannot invert; guess-and-check only")
assert len(a) == 64 and a != b and 80 < d < 180
print("OK: fingerprint verified")
