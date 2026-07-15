"""Key derivation and authenticated encryption. No vault knowledge here."""

import os

from argon2.low_level import Type, hash_secret_raw
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

SALT_LEN = 16
NONCE_LEN = 12  # AES-GCM standard nonce size
KEY_LEN = 32  # AES-256


def derive_key(password: str, salt: bytes) -> bytes:
    """Stretch a master password into a 32-byte key. Same inputs -> same key."""
    return hash_secret_raw(
        secret=password.encode(),
        salt=salt,
        time_cost=3,
        memory_cost=64 * 1024,  # 64 MiB — what makes GPU brute-force expensive
        parallelism=4,
        hash_len=KEY_LEN,
        type=Type.ID,  # Argon2id
    )


def encrypt(key: bytes, plaintext: bytes) -> bytes:
    """Returns nonce + ciphertext. Fresh random nonce every call — reuse breaks GCM."""
    nonce = os.urandom(NONCE_LEN)
    return nonce + AESGCM(key).encrypt(nonce, plaintext, None)


def decrypt(key: bytes, blob: bytes) -> bytes:
    """Raises cryptography.exceptions.InvalidTag on wrong key or tampered data."""
    return AESGCM(key).decrypt(blob[:NONCE_LEN], blob[NONCE_LEN:], None)
