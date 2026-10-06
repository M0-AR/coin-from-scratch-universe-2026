"""Part 1 — Fingerprints (SHA-256).

One-line primitive everything else builds on:
    sha256_hex("Alice pays Bob 30") -> 64 hex chars.

Properties verified in experiments/01_fingerprint.py:
  * deterministic, avalanche (~50% bits flip on 1-char change),
  * preimage resistant, fast to verify.
"""
from __future__ import annotations

import hashlib


def sha256_hex(data: str | bytes) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def sha256d_hex(data: str | bytes) -> str:
    """Double-SHA256 (Bitcoin header / txid convention)."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(hashlib.sha256(data).digest()).hexdigest()


_HEX2BIN = {
    "0": "0000", "1": "0001", "2": "0010", "3": "0011",
    "4": "0100", "5": "0101", "6": "0110", "7": "0111",
    "8": "1000", "9": "1001", "a": "1010", "b": "1011",
    "c": "1100", "d": "1101", "e": "1110", "f": "1111",
}


def hex_to_binary(h: str) -> str:
    return "".join(_HEX2BIN[c] for c in h.lower())


def hash_matches_difficulty_hex(hash_hex: str, difficulty: int) -> bool:
    """Naivecoin-style: `difficulty` = required leading ZERO HEX chars.

    Each extra zero is ~16x harder (vs 2x per binary zero).
    """
    return hash_hex.startswith("0" * difficulty)


def hash_matches_difficulty_bits(hash_hex: str, difficulty_bits: int) -> bool:
    """Bitcoin-style: `difficulty_bits` = required leading ZERO BITS."""
    return hex_to_binary(hash_hex).startswith("0" * difficulty_bits)


def hamming_distance_hex(h1: str, h2: str) -> int:
    """Bit-level distance — used to quantify the avalanche effect."""
    b1 = hex_to_binary(h1)
    b2 = hex_to_binary(h2)
    return sum(c1 != c2 for c1, c2 in zip(b1, b2))
